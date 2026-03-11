package org.matsim.project;

import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.Node;
import org.matsim.api.core.v01.network.NetworkWriter;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.population.routes.NetworkRoute;
import org.matsim.core.population.routes.RouteUtils;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.core.utils.misc.Time;
import org.matsim.pt.transitSchedule.api.Departure;
import org.matsim.pt.transitSchedule.api.TransitLine;
import org.matsim.pt.transitSchedule.api.TransitRoute;
import org.matsim.pt.transitSchedule.api.TransitRouteStop;
import org.matsim.pt.transitSchedule.api.TransitSchedule;
import org.matsim.pt.transitSchedule.api.TransitScheduleFactory;
import org.matsim.pt.transitSchedule.api.TransitScheduleWriter;
import org.matsim.pt.transitSchedule.api.TransitStopFacility;
import org.matsim.pt.utils.CreatePseudoNetwork;
import org.matsim.pt.utils.TransitScheduleValidator;
import org.matsim.vehicles.MatsimVehicleWriter;
import org.matsim.vehicles.Vehicle;
import org.matsim.vehicles.VehicleCapacity;
import org.matsim.vehicles.VehicleType;
import org.matsim.vehicles.VehicleUtils;
import org.matsim.vehicles.Vehicles;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.NavigableSet;
import java.util.PriorityQueue;
import java.util.Set;
import java.util.TreeSet;

/**
 * Creates bootstrap PT supply from stop data and assumptions.
 * Supports:
 * - legacy OSM stop CSV (no explicit routes): builds one outbound + one inbound line
 * - tagged route CSV with route_id/stop_seq/stop_id/name/x/y and optional dwell_sec: builds one line per route_id
 *   with outbound+inbound route variants. If dwell_sec column is present, per-stop dwell is used (seconds).
 * - Service profile CSV (pt_service_profile.csv) may include optional speed_kmh per route for travel time.
 * <p>
 * Assumptions and validation: see analysis-artifacts/pt-data/PT_ASSUMPTIONS_AND_VALIDATION.md.
 */
public class PrepareShamalganTransitFromAssumptions {

	private static final String TARGET_CRS = "EPSG:32643";
	private static final double DEFAULT_SPEED_KMH = 30.0;
	private static final double DEFAULT_DWELL_SEC = 60.0;
	private static final int DEFAULT_HEADWAY_SEC = 360;
	private static final String DEFAULT_SERVICE_START = "06:00:00";
	private static final String DEFAULT_SERVICE_END = "23:00:00";
	private static final String DEFAULT_SERVICE_PROFILE_CSV = "scenarios/shamalgan/pt_service_profile.csv";
	private static final int DEFAULT_LAYOVER_SEC = 300;
	private static final String DEFAULT_STD_VEHICLE_TYPE = "bus_std";
	private static final String DEFAULT_MINIBUS_VEHICLE_TYPE = "minibus";
	private static final int DEFAULT_STD_SEATS = 35;
	private static final int DEFAULT_STD_STANDING = 30;
	private static final double DEFAULT_STD_LENGTH_M = 12.0;
	private static final double DEFAULT_STD_PCU = 2.5;
	private static final int DEFAULT_MINIBUS_SEATS = 18;
	private static final int DEFAULT_MINIBUS_STANDING = 8;
	private static final double DEFAULT_MINIBUS_LENGTH_M = 7.5;
	private static final double DEFAULT_MINIBUS_PCU = 1.8;

	private static final Map<String, Integer> ROUTE_HEADWAY_OVERRIDES_SEC = Map.of(
		"6", 600,
		"11", 720,
		"213", 1200,
		"256", 1200
	);
	private static final Map<String, Integer> ROUTE_YANDEX_TARGET_AVG_HEADWAY_SEC = Map.of(
		"6", 1800,
		"11", 900,
		"213", 600
	);
	private static final Set<String> ROUTE_256_ALLOWED_ORIGIDS = Set.of("1384364335", "1233850824");
	private static final Map<String, String> ROUTE_MANDATORY_LINK_OVERRIDES = Map.of(
		// Corridor is tagged as osm_id=19687588 in new_map.gpkg (map__multilinestrings).
		// In the road network extraction this corridor is represented by multiple origids; link 2011
		// is used as an anchor to force route_213 through that branch.
		"213", "2011"
	);
	private static final Set<String> ROUTE_213_BLOCKED_ORIGIDS = Set.of("1154458994", "230099145");
	private static final double MAX_FORCED_SEGMENT_DETOUR_RATIO = 6.0;
	private static final Map<String, String> ROUTE_VEHICLE_TYPE_OVERRIDES = Map.of(
		"256", DEFAULT_MINIBUS_VEHICLE_TYPE,
		"6", DEFAULT_STD_VEHICLE_TYPE,
		"11", DEFAULT_STD_VEHICLE_TYPE,
		"213", DEFAULT_STD_VEHICLE_TYPE
	);

	private record StopSeed(String id, String name, double lon, double lat) {
	}

	/** Use dwellSec < 0 to mean "use default dwell". */
	private record TaggedStopSeed(String routeId, int stopSeq, String stopId, String name, double x, double y, double dwellSec) {
	}

	private record MappedStop(String id, Coord coord, Id<Link> linkId) {
	}

	private record DijkstraResult(boolean reachable, double distanceM, List<Link> links) {
	}

	private record NodeDist(Node node, double dist) {
	}

	private record ServicePeriod(double startSec, double endSec, int headwaySec) {
	}

	/** speedKmh &lt; 0 means use default. */
	private record RouteServiceProfile(
		String routeId,
		String vehicleTypeId,
		int seats,
		int standing,
		double lengthM,
		double pcu,
		int layoverSec,
		List<ServicePeriod> periods,
		double speedKmh
	) {
	}

	/** speedMps &lt; 0 means use default. */
	private record RouteOperationPlan(
		List<Double> departuresSec,
		int minHeadwaySec,
		int layoverSec,
		String vehicleTypeId,
		int seats,
		int standing,
		double lengthM,
		double pcu,
		double speedMps
	) {
	}

	public static void main(String[] args) throws Exception {
		if (args.length < 5) {
			System.out.println("Usage:");
			System.out.println("  PrepareShamalganTransitFromAssumptions <input-network.xml> <stops.csv> <output-network-with-pt.xml> <output-transitSchedule.xml> <output-transitVehicles.xml> [speedKmh] [dwellSec] [headwaySec] [serviceStart] [serviceEnd] [serviceProfileCsv]");
			System.out.println("stops.csv can be:");
			System.out.println("  legacy: osm_type,osm_id,name,lon,lat");
			System.out.println("  tagged: route_id,stop_seq,stop_id,name,x,y");
			return;
		}

		String inputNetwork = args[0];
		String stopsCsv = args[1];
		String outputNetworkWithPt = args[2];
		String outputTransitSchedule = args[3];
		String outputTransitVehicles = args[4];
		double speedKmh = args.length >= 6 ? Double.parseDouble(args[5]) : DEFAULT_SPEED_KMH;
		double dwellSec = args.length >= 7 ? Double.parseDouble(args[6]) : DEFAULT_DWELL_SEC;
		int headwaySec = args.length >= 8 ? Integer.parseInt(args[7]) : DEFAULT_HEADWAY_SEC;
		String serviceStart = args.length >= 9 ? args[8] : DEFAULT_SERVICE_START;
		String serviceEnd = args.length >= 10 ? args[9] : DEFAULT_SERVICE_END;
		String serviceProfileCsv = args.length >= 11 ? args[10] : DEFAULT_SERVICE_PROFILE_CSV;

		if (!Files.exists(Path.of(inputNetwork))) {
			throw new IllegalArgumentException("Network file not found: " + Path.of(inputNetwork).toAbsolutePath());
		}
		if (!Files.exists(Path.of(stopsCsv))) {
			throw new IllegalArgumentException("Stops CSV not found: " + Path.of(stopsCsv).toAbsolutePath());
		}

		Config config = ConfigUtils.createConfig();
		config.global().setCoordinateSystem(TARGET_CRS);
		config.network().setInputFile(inputNetwork);
		config.transit().setUseTransit(true);
		Scenario scenario = ScenarioUtils.loadScenario(config);

		Network network = scenario.getNetwork();
		TransitSchedule schedule = scenario.getTransitSchedule();
		Vehicles transitVehicles = scenario.getTransitVehicles();
		TransitScheduleFactory f = schedule.getFactory();

		double speedMps = speedKmh / 3.6;
		double serviceStartSec = Time.parseTime(serviceStart);
		double serviceEndSec = Time.parseTime(serviceEnd);
		if (!(serviceStartSec < serviceEndSec)) {
			throw new IllegalArgumentException("serviceStart must be before serviceEnd");
		}

		createVehicleType(transitVehicles, "busType_assumed", speedMps, DEFAULT_STD_SEATS, DEFAULT_STD_STANDING, DEFAULT_STD_LENGTH_M, DEFAULT_STD_PCU);

		Map<String, RouteServiceProfile> routeServiceProfiles = readRouteServiceProfiles(
			serviceProfileCsv,
			serviceStartSec,
			serviceEndSec,
			headwaySec
		);
		if (!routeServiceProfiles.isEmpty()) {
			System.out.println("Loaded service profile routes: " + routeServiceProfiles.size() + " from " + Path.of(serviceProfileCsv).toAbsolutePath());
		}

		boolean taggedRouteCsv = isTaggedRouteCsv(stopsCsv);
		if (taggedRouteCsv) {
			buildFromTaggedRouteCsv(
				stopsCsv, network, schedule, transitVehicles, f,
				speedMps, dwellSec, serviceStartSec, serviceEndSec, headwaySec,
				routeServiceProfiles
			);
		} else {
			buildFromLegacyCsv(
				stopsCsv, network, schedule, transitVehicles, f,
				speedMps, dwellSec, serviceStartSec, serviceEndSec, headwaySec
			);
		}

		if (!taggedRouteCsv) {
			new CreatePseudoNetwork(schedule, network, "pt_", speedMps, 10000.0).createNetwork();
		}

		var validation = TransitScheduleValidator.validateAll(schedule, network);
		if (!validation.isValid()) {
			System.out.println("Transit schedule validator reported issues:");
			TransitScheduleValidator.printResult(validation);
		}

		Path outNetwork = Path.of(outputNetworkWithPt);
		Path outSchedule = Path.of(outputTransitSchedule);
		Path outVehicles = Path.of(outputTransitVehicles);
		if (outNetwork.getParent() != null) Files.createDirectories(outNetwork.getParent());
		if (outSchedule.getParent() != null) Files.createDirectories(outSchedule.getParent());
		if (outVehicles.getParent() != null) Files.createDirectories(outVehicles.getParent());

		new NetworkWriter(network).write(outNetwork.toString());
		new TransitScheduleWriter(schedule).writeFile(outSchedule.toString());
		new MatsimVehicleWriter(transitVehicles).writeFile(outVehicles.toString());

		System.out.println("Assumed PT supply created.");
		System.out.println("Lines created: " + schedule.getTransitLines().size());
		System.out.println("Headway default sec: " + headwaySec + " ; service: " + serviceStart + " - " + serviceEnd);
		System.out.println("Speed km/h: " + speedKmh + " ; dwell sec: " + dwellSec);
		System.out.println("Network with PT: " + outNetwork.toAbsolutePath());
		System.out.println("Transit schedule: " + outSchedule.toAbsolutePath());
		System.out.println("Transit vehicles: " + outVehicles.toAbsolutePath());
	}

	private static boolean isTaggedRouteCsv(String path) throws Exception {
		List<String> lines = Files.readAllLines(Path.of(path), StandardCharsets.UTF_8);
		if (lines.isEmpty()) return false;
		String[] header = lines.get(0).split(",", -1);
		return findColumn(header, "route_id") >= 0 && findColumn(header, "stop_seq") >= 0;
	}

	private static void buildFromLegacyCsv(
		String stopsCsv,
		Network network,
		TransitSchedule schedule,
		Vehicles transitVehicles,
		TransitScheduleFactory f,
		double speedMps,
		double dwellSec,
		double serviceStartSec,
		double serviceEndSec,
		int headwaySec
	) throws Exception {
		List<StopSeed> seeds = readStopsCsv(stopsCsv);
		if (seeds.size() < 2) {
			throw new IllegalStateException("Need at least 2 bus stops, found: " + seeds.size());
		}

		CoordinateTransformation tx = TransformationFactory.getCoordinateTransformation(
			TransformationFactory.WGS84,
			TARGET_CRS
		);
		List<MappedStop> mapped = mapStopsToNetwork(seeds, tx, network, f, schedule);
		List<MappedStop> ordered = orderByNearestNeighbor(mapped);

		TransitLine outbound = createLine(
			schedule, f, transitVehicles,
			"line_bus_assumed_outbound", "route_outbound",
			ordered, speedMps, dwellSec, serviceStartSec, serviceEndSec, headwaySec
		);
		TransitLine inbound = createLine(
			schedule, f, transitVehicles,
			"line_bus_assumed_inbound", "route_inbound",
			reversedCopy(ordered), speedMps, dwellSec, serviceStartSec, serviceEndSec, headwaySec
		);
		schedule.addTransitLine(outbound);
		schedule.addTransitLine(inbound);
	}

	private static void buildFromTaggedRouteCsv(
		String stopsCsv,
		Network network,
		TransitSchedule schedule,
		Vehicles transitVehicles,
		TransitScheduleFactory f,
		double speedMps,
		double dwellSec,
		double serviceStartSec,
		double serviceEndSec,
		int defaultHeadwaySec,
		Map<String, RouteServiceProfile> routeServiceProfiles
	) throws Exception {
		List<TaggedStopSeed> tagged = readTaggedStopsCsv(stopsCsv);
		if (tagged.isEmpty()) {
			throw new IllegalStateException("No tagged route-stop rows found in: " + stopsCsv);
		}

		boolean hasPerStopDwell = tagged.stream().anyMatch(s -> s.dwellSec() >= 0);

		Map<String, MappedStop> stopByIdOut = new HashMap<>();
		Map<String, MappedStop> stopByIdIn = new HashMap<>();
		for (TaggedStopSeed s : tagged) {
			if (stopByIdOut.containsKey(s.stopId)) continue;
			Coord c = new Coord(s.x, s.y);
			Link link = org.matsim.core.network.NetworkUtils.getNearestLinkExactly(network, c);
			String stopName = s.name == null || s.name.isBlank() ? s.stopId : s.name;

			String outStopId = s.stopId;
			Id<TransitStopFacility> outFacId = Id.create("ptStop_" + outStopId, TransitStopFacility.class);
			TransitStopFacility outFac = f.createTransitStopFacility(outFacId, c, false);
			outFac.setName(stopName);
			outFac.setLinkId(link.getId());
			schedule.addStopFacility(outFac);
			stopByIdOut.put(s.stopId, new MappedStop(outStopId, c, link.getId()));

			Link reverse = findReverseLink(link);
			Link inboundLink = reverse != null ? reverse : link;
			String inStopId = s.stopId + ".1";
			Id<TransitStopFacility> inFacId = Id.create("ptStop_" + inStopId, TransitStopFacility.class);
			TransitStopFacility inFac = f.createTransitStopFacility(inFacId, c, false);
			inFac.setName(stopName);
			inFac.setLinkId(inboundLink.getId());
			schedule.addStopFacility(inFac);
			stopByIdIn.put(s.stopId, new MappedStop(inStopId, c, inboundLink.getId()));
		}

		Map<String, List<TaggedStopSeed>> byRoute = new HashMap<>();
		for (TaggedStopSeed s : tagged) {
			byRoute.computeIfAbsent(s.routeId, k -> new ArrayList<>()).add(s);
		}

		for (Map.Entry<String, List<TaggedStopSeed>> e : byRoute.entrySet()) {
			String routeId = e.getKey();
			List<TaggedStopSeed> rows = e.getValue();
			rows.sort(Comparator.comparingInt(TaggedStopSeed::stopSeq));
			if (rows.size() < 2) {
				System.out.println("Skipping route " + routeId + " (needs >=2 stops, found " + rows.size() + ")");
				continue;
			}

			List<MappedStop> orderedOut = new ArrayList<>();
			List<MappedStop> orderedInBase = new ArrayList<>();
			List<Double> dwellsOut = hasPerStopDwell ? new ArrayList<>() : null;
			for (TaggedStopSeed row : rows) {
				orderedOut.add(stopByIdOut.get(row.stopId));
				orderedInBase.add(stopByIdIn.get(row.stopId));
				if (dwellsOut != null) {
					dwellsOut.add(row.dwellSec() >= 0 ? row.dwellSec() : dwellSec);
				}
			}
			List<MappedStop> outbound = orderedOut;
			List<MappedStop> inbound = reversedCopy(orderedInBase);
			List<Double> dwellsIn = dwellsOut != null ? reversedCopyDouble(dwellsOut) : null;

			RouteOperationPlan operationPlan = buildRouteOperationPlan(
				routeId,
				routeServiceProfiles,
				serviceStartSec,
				serviceEndSec,
				defaultHeadwaySec
			);
			createVehicleType(
				transitVehicles,
				operationPlan.vehicleTypeId(),
				speedMps,
				operationPlan.seats(),
				operationPlan.standing(),
				operationPlan.lengthM(),
				operationPlan.pcu()
			);
			TransitLine line = f.createTransitLine(Id.create("line_" + routeId, TransitLine.class));
			TransitRoute routeOut = createRoadRoute(
				schedule,
				f,
				transitVehicles,
				network,
				routeId,
				"route_" + routeId + "_outbound",
				outbound,
				speedMps,
				dwellSec,
				dwellsOut,
				operationPlan
			);
			TransitRoute routeIn = createRoadRoute(
				schedule,
				f,
				transitVehicles,
				network,
				routeId,
				"route_" + routeId + "_inbound",
				inbound,
				speedMps,
				dwellSec,
				dwellsIn,
				operationPlan
			);
			line.addRoute(routeOut);
			line.addRoute(routeIn);
			schedule.addTransitLine(line);
		}
	}

	private static List<StopSeed> readStopsCsv(String path) throws Exception {
		List<String> lines = Files.readAllLines(Path.of(path), StandardCharsets.UTF_8);
		if (lines.isEmpty()) return List.of();

		String[] header = lines.get(0).split(",", -1);
		int idxType = findColumn(header, "osm_type");
		int idxId = findColumn(header, "osm_id");
		int idxName = findColumn(header, "name");
		int idxLon = findColumn(header, "lon");
		int idxLat = findColumn(header, "lat");
		if (idxType < 0 || idxId < 0 || idxName < 0 || idxLon < 0 || idxLat < 0) {
			throw new IllegalArgumentException("Unexpected legacy bus stop CSV header in " + path);
		}

		List<StopSeed> out = new ArrayList<>();
		for (int i = 1; i < lines.size(); i++) {
			String line = lines.get(i);
			if (line == null || line.isBlank()) continue;
			String[] p = line.split(",", -1);
			if (p.length <= Math.max(Math.max(idxLat, idxLon), idxName)) continue;
			String type = p[idxType].trim();
			String id = p[idxId].trim();
			String name = p[idxName].trim();
			double lon = Double.parseDouble(p[idxLon].trim());
			double lat = Double.parseDouble(p[idxLat].trim());
			String stopId = type + "_" + id;
			out.add(new StopSeed(stopId, name.isEmpty() ? stopId : name, lon, lat));
		}
		return out;
	}

	private static List<TaggedStopSeed> readTaggedStopsCsv(String path) throws Exception {
		List<String> lines = Files.readAllLines(Path.of(path), StandardCharsets.UTF_8);
		if (lines.isEmpty()) return List.of();

		String[] header = lines.get(0).split(",", -1);
		int idxRoute = findColumn(header, "route_id");
		int idxSeq = findColumn(header, "stop_seq");
		int idxStopId = findColumn(header, "stop_id");
		int idxName = findColumn(header, "name");
		int idxX = findColumn(header, "x");
		int idxY = findColumn(header, "y");
		int idxDwell = findColumn(header, "dwell_sec");
		if (idxRoute < 0 || idxSeq < 0 || idxStopId < 0 || idxName < 0 || idxX < 0 || idxY < 0) {
			throw new IllegalArgumentException("Unexpected tagged route CSV header in " + path);
		}

		List<TaggedStopSeed> out = new ArrayList<>();
		for (int i = 1; i < lines.size(); i++) {
			String line = lines.get(i);
			if (line == null || line.isBlank()) continue;
			String[] p = line.split(",", -1);
			int req = Math.max(idxY, Math.max(idxX, Math.max(idxName, Math.max(idxStopId, Math.max(idxSeq, idxRoute)))));
			if (p.length <= req) continue;
			String routeId = p[idxRoute].trim();
			int stopSeq = Integer.parseInt(p[idxSeq].trim());
			String stopId = p[idxStopId].trim();
			String name = p[idxName].trim();
			double x = Double.parseDouble(p[idxX].trim());
			double y = Double.parseDouble(p[idxY].trim());
			double dwellSec = -1.0;
			if (idxDwell >= 0 && p.length > idxDwell) {
				String dwellStr = getCsvCell(p, idxDwell);
				if (!dwellStr.isBlank()) {
					try {
						dwellSec = Double.parseDouble(dwellStr.trim());
					} catch (NumberFormatException ignored) { }
				}
			}
			out.add(new TaggedStopSeed(routeId, stopSeq, stopId, name, x, y, dwellSec));
		}
		return out;
	}

	private static Map<String, RouteServiceProfile> readRouteServiceProfiles(
		String path,
		double defaultServiceStartSec,
		double defaultServiceEndSec,
		int defaultHeadwaySec
	) throws Exception {
		if (path == null || path.isBlank()) return Map.of();
		Path csv = Path.of(path);
		if (!Files.exists(csv)) return Map.of();

		List<String> lines = Files.readAllLines(csv, StandardCharsets.UTF_8);
		if (lines.isEmpty()) return Map.of();

		String[] header = lines.get(0).split(",", -1);
		int idxRoute = findColumn(header, "route_id");
		int idxStart = findColumn(header, "period_start");
		int idxEnd = findColumn(header, "period_end");
		int idxHeadway = findColumn(header, "headway_sec");
		if (idxRoute < 0 || idxStart < 0 || idxEnd < 0 || idxHeadway < 0) {
			throw new IllegalArgumentException("Unexpected service profile CSV header in " + path);
		}

		int idxVehicleType = findColumn(header, "vehicle_type");
		int idxSeats = findColumn(header, "seats");
		int idxStanding = findColumn(header, "standing");
		int idxLength = findColumn(header, "length_m");
		int idxPcu = findColumn(header, "pcu");
		int idxLayover = findColumn(header, "layover_sec");
		int idxSpeedKmh = findColumn(header, "speed_kmh");

		Map<String, List<ServicePeriod>> periodsByRoute = new HashMap<>();
		Map<String, String> vehicleTypeByRoute = new HashMap<>();
		Map<String, Integer> seatsByRoute = new HashMap<>();
		Map<String, Integer> standingByRoute = new HashMap<>();
		Map<String, Double> lengthByRoute = new HashMap<>();
		Map<String, Double> pcuByRoute = new HashMap<>();
		Map<String, Integer> layoverByRoute = new HashMap<>();
		Map<String, Double> speedKmhByRoute = new HashMap<>();

		for (int i = 1; i < lines.size(); i++) {
			String line = lines.get(i);
			if (line == null || line.isBlank()) continue;
			String[] p = line.split(",", -1);

			String routeId = getCsvCell(p, idxRoute);
			if (routeId.isBlank()) continue;

			double periodStart = parseTimeOrDefault(getCsvCell(p, idxStart), defaultServiceStartSec);
			double periodEnd = parseTimeOrDefault(getCsvCell(p, idxEnd), defaultServiceEndSec);
			if (!(periodStart < periodEnd)) continue;
			int headway = Math.max(60, parseIntOrDefault(getCsvCell(p, idxHeadway), defaultHeadwaySec));
			periodsByRoute.computeIfAbsent(routeId, k -> new ArrayList<>()).add(new ServicePeriod(periodStart, periodEnd, headway));

			String vehicleType = getCsvCell(p, idxVehicleType);
			if (!vehicleType.isBlank()) vehicleTypeByRoute.put(routeId, vehicleType);

			String seats = getCsvCell(p, idxSeats);
			if (!seats.isBlank()) seatsByRoute.put(routeId, parseIntOrDefault(seats, defaultSeatsForVehicleType(vehicleType)));

			String standing = getCsvCell(p, idxStanding);
			if (!standing.isBlank()) standingByRoute.put(routeId, parseIntOrDefault(standing, defaultStandingForVehicleType(vehicleType)));

			String length = getCsvCell(p, idxLength);
			if (!length.isBlank()) lengthByRoute.put(routeId, parseDoubleOrDefault(length, defaultLengthForVehicleType(vehicleType)));

			String pcu = getCsvCell(p, idxPcu);
			if (!pcu.isBlank()) pcuByRoute.put(routeId, parseDoubleOrDefault(pcu, defaultPcuForVehicleType(vehicleType)));

			String layover = getCsvCell(p, idxLayover);
			if (!layover.isBlank()) layoverByRoute.put(routeId, Math.max(0, parseIntOrDefault(layover, DEFAULT_LAYOVER_SEC)));

			if (idxSpeedKmh >= 0 && p.length > idxSpeedKmh) {
				String speedStr = getCsvCell(p, idxSpeedKmh);
				if (!speedStr.isBlank()) {
					double kmh = parseDoubleOrDefault(speedStr, -1.0);
					if (kmh > 0) speedKmhByRoute.put(routeId, kmh);
				}
			}
		}

		Map<String, RouteServiceProfile> out = new HashMap<>();
		for (Map.Entry<String, List<ServicePeriod>> e : periodsByRoute.entrySet()) {
			String routeId = e.getKey();
			List<ServicePeriod> periods = new ArrayList<>(e.getValue());
			periods.sort(Comparator.comparingDouble(ServicePeriod::startSec));

			String vehicleTypeId = vehicleTypeByRoute.getOrDefault(
				routeId,
				ROUTE_VEHICLE_TYPE_OVERRIDES.getOrDefault(routeId, DEFAULT_STD_VEHICLE_TYPE)
			);
			int seats = seatsByRoute.getOrDefault(routeId, defaultSeatsForVehicleType(vehicleTypeId));
			int standing = standingByRoute.getOrDefault(routeId, defaultStandingForVehicleType(vehicleTypeId));
			double lengthM = lengthByRoute.getOrDefault(routeId, defaultLengthForVehicleType(vehicleTypeId));
			double pcu = pcuByRoute.getOrDefault(routeId, defaultPcuForVehicleType(vehicleTypeId));
			int layoverSec = layoverByRoute.getOrDefault(routeId, DEFAULT_LAYOVER_SEC);
			double speedKmh = speedKmhByRoute.getOrDefault(routeId, -1.0);

			out.put(
				routeId,
				new RouteServiceProfile(routeId, vehicleTypeId, seats, standing, lengthM, pcu, layoverSec, periods, speedKmh)
			);
		}
		return out;
	}

	private static RouteOperationPlan buildRouteOperationPlan(
		String routeId,
		Map<String, RouteServiceProfile> serviceProfiles,
		double serviceStartSec,
		double serviceEndSec,
		int defaultHeadwaySec
	) {
		RouteServiceProfile profile = serviceProfiles.get(routeId);
		if (profile != null) {
			List<ServicePeriod> periods = calibratePeriodsToTargetAverage(routeId, profile.periods(), serviceStartSec, serviceEndSec);
			List<Double> departures = buildDepartureTimes(periods, serviceStartSec, serviceEndSec);
			int minHeadway = periods.stream().mapToInt(ServicePeriod::headwaySec).min().orElse(defaultHeadwaySec);
			double speedMps = profile.speedKmh() > 0 ? (profile.speedKmh() / 3.6) : -1.0;
			return new RouteOperationPlan(
				departures,
				Math.max(60, minHeadway),
				profile.layoverSec(),
				profile.vehicleTypeId(),
				profile.seats(),
				profile.standing(),
				profile.lengthM(),
				profile.pcu(),
				speedMps
			);
		}

		int fallbackHeadway = ROUTE_HEADWAY_OVERRIDES_SEC.getOrDefault(routeId, defaultHeadwaySec);
		String vehicleTypeId = ROUTE_VEHICLE_TYPE_OVERRIDES.getOrDefault(routeId, DEFAULT_STD_VEHICLE_TYPE);
		List<Double> departures = buildDepartureTimes(
			List.of(new ServicePeriod(serviceStartSec, serviceEndSec, fallbackHeadway)),
			serviceStartSec,
			serviceEndSec
		);
		return new RouteOperationPlan(
			departures,
			Math.max(60, fallbackHeadway),
			DEFAULT_LAYOVER_SEC,
			vehicleTypeId,
			defaultSeatsForVehicleType(vehicleTypeId),
			defaultStandingForVehicleType(vehicleTypeId),
			defaultLengthForVehicleType(vehicleTypeId),
			defaultPcuForVehicleType(vehicleTypeId),
			-1.0
		);
	}

	private static List<Double> buildDepartureTimes(List<ServicePeriod> periods, double serviceStartSec, double serviceEndSec) {
		List<ServicePeriod> ordered = new ArrayList<>(periods);
		ordered.sort(Comparator.comparingDouble(ServicePeriod::startSec));

		List<Integer> departures = new ArrayList<>();
		Double lastDep = null;

		for (ServicePeriod period : ordered) {
			double start = Math.max(period.startSec(), serviceStartSec);
			double end = Math.min(period.endSec(), serviceEndSec);
			if (!(start <= end)) continue;

			int headway = Math.max(60, period.headwaySec());
			double dep;
			if (lastDep == null) {
				dep = start;
			} else {
				dep = lastDep + headway;
				while (dep + 1e-9 < start) {
					dep += headway;
				}
			}

			for (; dep <= end + 1e-9; dep += headway) {
				int rounded = (int) Math.round(dep);
				if (departures.isEmpty() || departures.get(departures.size() - 1) != rounded) {
					departures.add(rounded);
					lastDep = dep;
				}
			}
		}

		if (departures.isEmpty()) {
			departures.add((int) Math.round(serviceStartSec));
		}

		List<Double> out = new ArrayList<>();
		for (Integer dep : departures) out.add(dep.doubleValue());
		return out;
	}

	private static List<ServicePeriod> calibratePeriodsToTargetAverage(
		String routeId,
		List<ServicePeriod> periods,
		double serviceStartSec,
		double serviceEndSec
	) {
		Integer targetAvg = ROUTE_YANDEX_TARGET_AVG_HEADWAY_SEC.get(routeId);
		if (targetAvg == null || periods.isEmpty()) return new ArrayList<>(periods);

		double currentAvg = computeDurationWeightedAverageHeadway(periods, serviceStartSec, serviceEndSec);
		if (!(currentAvg > 0.0) || !Double.isFinite(currentAvg)) return new ArrayList<>(periods);

		double factor = targetAvg / currentAvg;
		List<ServicePeriod> adjusted = new ArrayList<>();
		for (ServicePeriod p : periods) {
			int scaled = roundToNearestMinute(Math.max(300.0, Math.min(3600.0, p.headwaySec() * factor)));
			adjusted.add(new ServicePeriod(p.startSec(), p.endSec(), scaled));
		}

		double adjustedAvg = computeDurationWeightedAverageHeadway(adjusted, serviceStartSec, serviceEndSec);
		System.out.println(
			"Route " + routeId + " headway calibration: sourceAvg=" + String.format("%.1f", currentAvg)
				+ "s, targetAvg=" + targetAvg + "s, adjustedAvg=" + String.format("%.1f", adjustedAvg) + "s"
		);
		return adjusted;
	}

	private static double computeDurationWeightedAverageHeadway(
		List<ServicePeriod> periods,
		double serviceStartSec,
		double serviceEndSec
	) {
		double weighted = 0.0;
		double durationSum = 0.0;
		for (ServicePeriod p : periods) {
			double start = Math.max(serviceStartSec, p.startSec());
			double end = Math.min(serviceEndSec, p.endSec());
			double duration = end - start;
			if (!(duration > 0.0)) continue;
			weighted += duration * p.headwaySec();
			durationSum += duration;
		}
		if (!(durationSum > 0.0)) return Double.NaN;
		return weighted / durationSum;
	}

	private static int roundToNearestMinute(double seconds) {
		return (int) (Math.round(seconds / 60.0) * 60);
	}

	private static String getCsvCell(String[] row, int idx) {
		if (idx < 0 || idx >= row.length) return "";
		return row[idx].trim();
	}

	private static int parseIntOrDefault(String value, int fallback) {
		if (value == null || value.isBlank()) return fallback;
		try {
			return Integer.parseInt(value.trim());
		} catch (NumberFormatException e) {
			return fallback;
		}
	}

	private static double parseDoubleOrDefault(String value, double fallback) {
		if (value == null || value.isBlank()) return fallback;
		try {
			return Double.parseDouble(value.trim());
		} catch (NumberFormatException e) {
			return fallback;
		}
	}

	private static double parseTimeOrDefault(String value, double fallback) {
		if (value == null || value.isBlank()) return fallback;
		return Time.parseTime(value.trim());
	}

	private static int findColumn(String[] header, String name) {
		for (int i = 0; i < header.length; i++) {
			String col = header[i] == null ? "" : header[i].replace("\uFEFF", "").trim();
			if (name.equalsIgnoreCase(col)) return i;
		}
		return -1;
	}

	private static List<MappedStop> mapStopsToNetwork(
		List<StopSeed> seeds,
		CoordinateTransformation tx,
		Network network,
		TransitScheduleFactory f,
		TransitSchedule schedule
	) {
		List<MappedStop> mapped = new ArrayList<>();
		for (StopSeed s : seeds) {
			Coord c = tx.transform(new Coord(s.lon, s.lat));
			Link link = org.matsim.core.network.NetworkUtils.getNearestLinkExactly(network, c);
			Id<TransitStopFacility> facId = Id.create("ptStop_" + s.id, TransitStopFacility.class);
			TransitStopFacility fac = f.createTransitStopFacility(facId, c, false);
			fac.setName(s.name);
			fac.setLinkId(link.getId());
			schedule.addStopFacility(fac);
			mapped.add(new MappedStop(s.id, c, link.getId()));
		}
		return mapped;
	}

	private static List<MappedStop> orderByNearestNeighbor(List<MappedStop> stops) {
		List<MappedStop> remaining = new ArrayList<>(stops);
		remaining.sort(Comparator.comparingDouble(s -> s.coord.getX()));
		List<MappedStop> ordered = new ArrayList<>();
		MappedStop current = remaining.remove(0);
		ordered.add(current);

		while (!remaining.isEmpty()) {
			MappedStop next = null;
			double best = Double.POSITIVE_INFINITY;
			for (MappedStop cand : remaining) {
				double d = dist(current.coord, cand.coord);
				if (d < best) {
					best = d;
					next = cand;
				}
			}
			ordered.add(next);
			remaining.remove(next);
			current = next;
		}
		return ordered;
	}

	private static List<MappedStop> reversedCopy(List<MappedStop> in) {
		List<MappedStop> out = new ArrayList<>();
		for (int i = in.size() - 1; i >= 0; i--) {
			out.add(in.get(i));
		}
		return out;
	}

	private static List<Double> reversedCopyDouble(List<Double> in) {
		List<Double> out = new ArrayList<>();
		for (int i = in.size() - 1; i >= 0; i--) {
			out.add(in.get(i));
		}
		return out;
	}

	private static TransitRoute createRoadRoute(
		TransitSchedule schedule,
		TransitScheduleFactory f,
		Vehicles vehicles,
		Network network,
		String baseRouteId,
		String routeId,
		List<MappedStop> ordered,
		double speedMps,
		double dwellSec,
		List<Double> dwellSecPerStop,
		RouteOperationPlan operationPlan
	) {
		List<TransitRouteStop> routeStops = new ArrayList<>();
		List<List<Link>> segmentPaths = new ArrayList<>();
		List<Double> segmentLengths = new ArrayList<>();
		double effectiveSpeedMps = (operationPlan.speedMps() > 0) ? operationPlan.speedMps() : speedMps;

		Set<String> allowedOrigids = "256".equals(baseRouteId) ? ROUTE_256_ALLOWED_ORIGIDS : null;
		Set<String> blockedOrigids = "213".equals(baseRouteId) ? ROUTE_213_BLOCKED_ORIGIDS : null;

		for (int i = 0; i < ordered.size() - 1; i++) {
			MappedStop from = ordered.get(i);
			MappedStop to = ordered.get(i + 1);
			List<Link> segLinks = buildSegmentPath(network, from, to, allowedOrigids, blockedOrigids);
			segmentPaths.add(segLinks);
			segmentLengths.add(totalLength(segLinks));
		}
		String mandatoryLinkId = ROUTE_MANDATORY_LINK_OVERRIDES.get(baseRouteId);
		if (mandatoryLinkId != null && !mandatoryLinkId.isBlank()) {
			Link mandatory = network.getLinks().get(Id.createLinkId(mandatoryLinkId));
			if (mandatory != null) {
				applyForcedMandatoryCorridor(
					routeId,
					ordered,
					network,
					segmentPaths,
					segmentLengths,
					mandatory,
					allowedOrigids,
					blockedOrigids
				);
			}
			if (!routeContainsLinkId(segmentPaths, mandatoryLinkId)) {
				throw new IllegalStateException(
					"Route " + routeId + " must include mandatory link " + mandatoryLinkId + " but it is missing."
				);
			}
		}
		if (blockedOrigids != null && !blockedOrigids.isEmpty()) {
			String blocked = firstBlockedOrigidPresent(segmentPaths, blockedOrigids);
			if (blocked != null) {
				throw new IllegalStateException(
					"Route " + routeId + " includes blocked origid " + blocked + " (rail crossing branch)."
				);
			}
		}

		List<Id<Link>> routeLinkIds = new ArrayList<>();
		for (List<Link> segLinks : segmentPaths) {
			for (Link l : segLinks) {
				if (routeLinkIds.isEmpty() || !routeLinkIds.get(routeLinkIds.size() - 1).equals(l.getId())) {
					routeLinkIds.add(l.getId());
				}
			}
		}
		if (routeLinkIds.size() < 2) {
			throw new IllegalStateException("Route " + routeId + " produced too few network links: " + routeLinkIds.size());
		}

		double offset = 0.0;
		for (int i = 0; i < ordered.size(); i++) {
			MappedStop ms = ordered.get(i);
			Id<TransitStopFacility> facId = Id.create("ptStop_" + ms.id, TransitStopFacility.class);
			TransitStopFacility fac = schedule.getFacilities().get(facId);
			if (fac == null) {
				throw new IllegalStateException("Missing transit stop facility: " + facId);
			}
			double stopDwell = (dwellSecPerStop != null && i < dwellSecPerStop.size())
				? dwellSecPerStop.get(i) : dwellSec;
			double arrival = offset;
			double departure = offset + stopDwell;
			routeStops.add(f.createTransitRouteStop(fac, arrival, departure));
			if (i < ordered.size() - 1) {
				offset = departure + (segmentLengths.get(i) / effectiveSpeedMps);
			}
		}

		NetworkRoute networkRoute = RouteUtils.createNetworkRoute(routeLinkIds);
		TransitRoute route = f.createTransitRoute(
			Id.create(routeId, TransitRoute.class),
			networkRoute,
			routeStops,
			"pt"
		);

		double lastStopDwell = routeStops.isEmpty() ? dwellSec : (
			(dwellSecPerStop != null && ordered.size() <= dwellSecPerStop.size())
				? dwellSecPerStop.get(ordered.size() - 1) : dwellSec);
		double oneWaySec = routeStops.isEmpty() ? 0.0 : offset + lastStopDwell;
		List<Double> departures = operationPlan.departuresSec().isEmpty() ? List.of(0.0) : operationPlan.departuresSec();
		int minHeadwaySec = Math.max(60, operationPlan.minHeadwaySec());
		int fleetSize = Math.max(1, (int) Math.ceil((oneWaySec + operationPlan.layoverSec()) / minHeadwaySec));
		fleetSize = Math.min(fleetSize, departures.size());

		Id<VehicleType> typeId = Id.create(operationPlan.vehicleTypeId(), VehicleType.class);
		if (!vehicles.getVehicleTypes().containsKey(typeId)) {
			throw new IllegalStateException("Vehicle type not found: " + typeId);
		}
		int depCount = 0;
		for (double dep : departures) {
			Id<Departure> depId = Id.create(routeId + "_dep_" + depCount, Departure.class);
			Departure departure = f.createDeparture(depId, dep);
			int slot = depCount % fleetSize;
			Id<Vehicle> vehicleId = Id.createVehicleId(routeId + "_veh_" + slot);
			if (!vehicles.getVehicles().containsKey(vehicleId)) {
				Vehicle veh = VehicleUtils.createVehicle(vehicleId, vehicles.getVehicleTypes().get(typeId));
				vehicles.addVehicle(veh);
			}
			departure.setVehicleId(vehicleId);
			route.addDeparture(departure);
			depCount++;
		}
		System.out.println(
			"Route " + routeId + ": departures=" + depCount + ", fleet=" + fleetSize
				+ ", vehicleType=" + operationPlan.vehicleTypeId()
		);
		return route;
	}

	private static void applyForcedMandatoryCorridor(
		String routeId,
		List<MappedStop> ordered,
		Network network,
		List<List<Link>> segmentPaths,
		List<Double> segmentLengths,
		Link mandatory,
		Set<String> allowedOrigids,
		Set<String> blockedOrigids
	) {
		double bestRatio = Double.POSITIVE_INFINITY;
		int bestIdx = -1;
		List<Link> bestForcedPath = null;
		double bestForcedLen = Double.NaN;

		for (int i = 0; i < segmentPaths.size(); i++) {
			MappedStop from = ordered.get(i);
			MappedStop to = ordered.get(i + 1);
			List<Link> forced = buildSegmentPathViaMandatoryLink(network, from, to, mandatory, allowedOrigids, blockedOrigids);
			if (forced == null || forced.isEmpty()) continue;
			double baseLen = segmentLengths.get(i);
			double forcedLen = totalLength(forced);
			if (!(baseLen > 0.0) || !Double.isFinite(forcedLen)) continue;
			double ratio = forcedLen / baseLen;
			if (ratio < bestRatio) {
				bestRatio = ratio;
				bestIdx = i;
				bestForcedPath = forced;
				bestForcedLen = forcedLen;
			}
		}

		if (bestIdx >= 0 && bestForcedPath != null && bestRatio <= MAX_FORCED_SEGMENT_DETOUR_RATIO) {
			segmentPaths.set(bestIdx, bestForcedPath);
			segmentLengths.set(bestIdx, bestForcedLen);
			System.out.println(
				"Applied mandatory corridor for " + routeId + " via link " + mandatory.getId()
					+ " on segment " + (bestIdx + 1) + " with detour ratio " + String.format("%.2f", bestRatio)
			);
		}
	}

	private static List<Link> buildSegmentPath(
		Network network,
		MappedStop from,
		MappedStop to,
		Set<String> allowedOrigids,
		Set<String> blockedOrigids
	) {
		Link fromLink = network.getLinks().get(from.linkId);
		Link toLink = network.getLinks().get(to.linkId);
		if (fromLink == null || toLink == null) {
			throw new IllegalStateException("Stop links not found in network for " + from.id + " -> " + to.id);
		}

		List<Link> out = new ArrayList<>();
		out.add(fromLink);
		if (!fromLink.getId().equals(toLink.getId())) {
			DijkstraResult core = shortestPathByLength(fromLink.getToNode(), toLink.getFromNode(), allowedOrigids, blockedOrigids);
			if (!core.reachable) {
				throw new IllegalStateException(
					"No directed path between stop links: " + from.id + " (" + fromLink.getId() + ") -> "
						+ to.id + " (" + toLink.getId() + ")"
				);
			}
			for (Link l : core.links) {
				if (!out.get(out.size() - 1).getId().equals(l.getId())) {
					out.add(l);
				}
			}
			if (!out.get(out.size() - 1).getId().equals(toLink.getId())) {
				out.add(toLink);
			}
		}
		return out;
	}

	private static List<Link> buildSegmentPathViaMandatoryLink(
		Network network,
		MappedStop from,
		MappedStop to,
		Link mandatory,
		Set<String> allowedOrigids,
		Set<String> blockedOrigids
	) {
		Link fromLink = network.getLinks().get(from.linkId);
		Link toLink = network.getLinks().get(to.linkId);
		if (fromLink == null || toLink == null) return null;

		DijkstraResult pre = shortestPathByLength(fromLink.getToNode(), mandatory.getFromNode(), allowedOrigids, blockedOrigids);
		DijkstraResult post = shortestPathByLength(mandatory.getToNode(), toLink.getFromNode(), allowedOrigids, blockedOrigids);
		if (!pre.reachable || !post.reachable) {
			return null;
		}

		List<Link> out = new ArrayList<>();
		appendUnique(out, fromLink);
		for (Link l : pre.links) appendUnique(out, l);
		appendUnique(out, mandatory);
		for (Link l : post.links) appendUnique(out, l);
		appendUnique(out, toLink);
		return out;
	}

	private static Link findReverseLink(Link link) {
		Node from = link.getFromNode();
		Node to = link.getToNode();
		Link best = null;
		double bestScore = Double.POSITIVE_INFINITY;
		for (Link cand : to.getOutLinks().values()) {
			if (!cand.getToNode().getId().equals(from.getId())) continue;
			double score = Math.abs(cand.getLength() - link.getLength());
			if (score < bestScore) {
				bestScore = score;
				best = cand;
			}
		}
		return best;
	}

	private static boolean routeContainsLinkId(List<List<Link>> segmentPaths, String linkId) {
		for (List<Link> seg : segmentPaths) {
			for (Link link : seg) {
				if (link.getId().toString().equals(linkId)) return true;
			}
		}
		return false;
	}

	private static String firstBlockedOrigidPresent(List<List<Link>> segmentPaths, Set<String> blockedOrigids) {
		for (List<Link> seg : segmentPaths) {
			for (Link link : seg) {
				String origid = getOrigid(link);
				if (blockedOrigids.contains(origid)) {
					return origid;
				}
			}
		}
		return null;
	}

	private static String getOrigid(Link link) {
		Object orig = link.getAttributes().getAttribute("origid");
		if (orig == null) return "";
		if (orig instanceof Number n) {
			double v = n.doubleValue();
			if (Double.isFinite(v)) {
				long rounded = Math.round(v);
				if (Math.abs(v - rounded) <= 1e-6 * Math.max(1.0, Math.abs(v))) {
					return Long.toString(rounded);
				}
			}
			return orig.toString().trim();
		}

		String s = orig.toString().trim();
		if (s.isEmpty()) return "";
		try {
			double v = Double.parseDouble(s);
			if (Double.isFinite(v)) {
				long rounded = Math.round(v);
				if (Math.abs(v - rounded) <= 1e-6 * Math.max(1.0, Math.abs(v))) {
					return Long.toString(rounded);
				}
			}
		} catch (NumberFormatException ignored) {
			// Keep original string representation for non-numeric origids.
		}
		return s;
	}

	private static void appendUnique(List<Link> links, Link link) {
		if (links.isEmpty() || !links.get(links.size() - 1).getId().equals(link.getId())) {
			links.add(link);
		}
	}

	private static double totalLength(List<Link> links) {
		return links.stream().mapToDouble(Link::getLength).sum();
	}

	private static DijkstraResult shortestPathByLength(Node start, Node goal, Set<String> allowedOrigids, Set<String> blockedOrigids) {
		if (start.getId().equals(goal.getId())) {
			return new DijkstraResult(true, 0.0, List.of());
		}

		Map<Id<Node>, Double> best = new HashMap<>();
		Map<Id<Node>, Link> inLink = new HashMap<>();
		Set<Id<Node>> done = new HashSet<>();
		PriorityQueue<NodeDist> pq = new PriorityQueue<>(Comparator.comparingDouble(n -> n.dist));
		best.put(start.getId(), 0.0);
		pq.add(new NodeDist(start, 0.0));

		while (!pq.isEmpty()) {
			NodeDist cur = pq.poll();
			Id<Node> curId = cur.node.getId();
			if (!done.add(curId)) continue;
			if (curId.equals(goal.getId())) break;

			for (Link out : cur.node.getOutLinks().values()) {
				String origid = getOrigid(out);
				if (blockedOrigids != null && blockedOrigids.contains(origid)) continue;
				if (allowedOrigids != null && !allowedOrigids.isEmpty()) {
					if (!allowedOrigids.contains(origid)) continue;
				}
				Node nxt = out.getToNode();
				Id<Node> nxtId = nxt.getId();
				double cand = cur.dist + out.getLength();
				double known = best.getOrDefault(nxtId, Double.POSITIVE_INFINITY);
				if (cand + 1e-9 < known) {
					best.put(nxtId, cand);
					inLink.put(nxtId, out);
					pq.add(new NodeDist(nxt, cand));
				}
			}
		}

		Double dist = best.get(goal.getId());
		if (dist == null || !Double.isFinite(dist)) {
			return new DijkstraResult(false, Double.NaN, List.of());
		}

		ArrayDeque<Link> path = new ArrayDeque<>();
		Id<Node> cur = goal.getId();
		while (!cur.equals(start.getId())) {
			Link step = inLink.get(cur);
			if (step == null) {
				return new DijkstraResult(false, Double.NaN, List.of());
			}
			path.addFirst(step);
			cur = step.getFromNode().getId();
		}
		return new DijkstraResult(true, dist, new ArrayList<>(path));
	}

	private static void createVehicleType(
		Vehicles vehicles,
		String typeName,
		double speedMps,
		int seats,
		int standing,
		double lengthM,
		double pcu
	) {
		Id<VehicleType> typeId = Id.create(typeName, VehicleType.class);
		if (vehicles.getVehicleTypes().containsKey(typeId)) return;

		VehicleType type = VehicleUtils.createVehicleType(typeId);
		type.setMaximumVelocity(speedMps);
		type.setNetworkMode("pt");
		type.setLength(lengthM);
		type.setPcuEquivalents(pcu);
		VehicleCapacity cap = type.getCapacity();
		cap.setSeats(seats);
		cap.setStandingRoom(standing);
		vehicles.addVehicleType(type);
	}

	private static boolean isMinibusType(String vehicleTypeId) {
		if (vehicleTypeId == null) return false;
		String v = vehicleTypeId.trim().toLowerCase();
		return v.contains("mini");
	}

	private static int defaultSeatsForVehicleType(String vehicleTypeId) {
		return isMinibusType(vehicleTypeId) ? DEFAULT_MINIBUS_SEATS : DEFAULT_STD_SEATS;
	}

	private static int defaultStandingForVehicleType(String vehicleTypeId) {
		return isMinibusType(vehicleTypeId) ? DEFAULT_MINIBUS_STANDING : DEFAULT_STD_STANDING;
	}

	private static double defaultLengthForVehicleType(String vehicleTypeId) {
		return isMinibusType(vehicleTypeId) ? DEFAULT_MINIBUS_LENGTH_M : DEFAULT_STD_LENGTH_M;
	}

	private static double defaultPcuForVehicleType(String vehicleTypeId) {
		return isMinibusType(vehicleTypeId) ? DEFAULT_MINIBUS_PCU : DEFAULT_STD_PCU;
	}

	private static TransitLine createLine(
		TransitSchedule schedule,
		TransitScheduleFactory f,
		Vehicles vehicles,
		String lineId,
		String routeId,
		List<MappedStop> ordered,
		double speedMps,
		double dwellSec,
		double serviceStartSec,
		double serviceEndSec,
		int headwaySec
	) {
		TransitLine line = f.createTransitLine(Id.create(lineId, TransitLine.class));
		List<TransitRouteStop> routeStops = new ArrayList<>();

		double offset = 0.0;
		for (int i = 0; i < ordered.size(); i++) {
			MappedStop ms = ordered.get(i);
			Id<TransitStopFacility> facId = Id.create("ptStop_" + ms.id, TransitStopFacility.class);
			TransitStopFacility fac = schedule.getFacilities().get(facId);
			double arrival = offset;
			double departure = offset + dwellSec;
			routeStops.add(f.createTransitRouteStop(fac, arrival, departure));
			if (i < ordered.size() - 1) {
				double runTime = dist(ms.coord, ordered.get(i + 1).coord) / speedMps;
				offset = departure + runTime;
			}
		}

		TransitRoute route = f.createTransitRoute(
			Id.create(routeId, TransitRoute.class),
			null,
			routeStops,
			"pt"
		);

		Id<VehicleType> typeId = Id.create("busType_assumed", VehicleType.class);
		int depCount = 0;
		for (double dep = serviceStartSec; dep <= serviceEndSec; dep += headwaySec) {
			Id<Departure> depId = Id.create(routeId + "_dep_" + depCount, Departure.class);
			Departure departure = f.createDeparture(depId, dep);
			Id<Vehicle> vehicleId = Id.createVehicleId(routeId + "_veh_" + depCount);
			Vehicle veh = VehicleUtils.createVehicle(vehicleId, vehicles.getVehicleTypes().get(typeId));
			vehicles.addVehicle(veh);
			departure.setVehicleId(vehicleId);
			route.addDeparture(departure);
			depCount++;
		}

		line.addRoute(route);
		return line;
	}

	private static double dist(Coord a, Coord b) {
		double dx = a.getX() - b.getX();
		double dy = a.getY() - b.getY();
		return Math.sqrt(dx * dx + dy * dy);
	}
}
