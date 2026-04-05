package org.matsim.project;

import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.NetworkWriter;
import org.matsim.api.core.v01.network.Node;
import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.contrib.osm.networkReader.SupersonicOsmNetworkReader;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.network.algorithms.NetworkCleaner;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.core.utils.io.OsmNetworkReader;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilderFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Builds a car network from OSM. Lane counts follow OSM tags where present, else defaults aligned with
 * {@code docs/ru/progress/10_final_report_shamalgan.md} (СН РК 3.03-01-2013 orienting capacities per lane).
 * <p>
 * Base capacity (before {@code poor}) is {@code capacityPerLane × numberOfLanes} per link direction.
 * Profile {@code poor} then scales capacity by {@code capacityMultiplier} (0.70–0.85) and caps free-flow speed
 * by speed class — see {@link #applyRoadConditionProfile}.
 */
public class PrepareShamalganNetwork {

	/** СН РК 3.03-01-2013 orienting range ~600–1400 veh/h/lane (continuous flow); model uses 1000. */
	private static final double CAP_PER_LANE_MAGISTRAL_VEH_H = 1000.0;
	/** Urban arterial orienting ~200–600; model uses 300. */
	private static final double CAP_PER_LANE_URBAN_ARTERIAL_VEH_H = 300.0;
	/** Local / residential orienting ~20–200; model uses 100. */
	private static final double CAP_PER_LANE_LOCAL_VEH_H = 100.0;

	/**
	 * Proxy for {@code traffic_signals} / {@code crossing=traffic_signals} from OSM.
	 * <p>
	 * We don't model signal phases, but we reduce capacity and free-flow speed on links adjacent
	 * to signalized intersections to represent signal delays.
	 */
	private static final double TRAFFIC_SIGNAL_CAPACITY_MULT = 0.85;
	private static final double TRAFFIC_SIGNAL_FREESPEED_MULT = 0.90;

	public static void main(String[] args) {
		if (args.length < 2) {
			System.out.println("Usage:");
			System.out.println("  PrepareShamalganNetwork <input.osm/.osm.pbf> <output-network.xml> [targetCrs] [roadProfile]");
			System.out.println("Example:");
			System.out.println("  PrepareShamalganNetwork original-input-data/shamalgan/map scenarios/shamalgan/network.xml EPSG:32643 poor");
			return;
		}

		String inputOsm = args[0];
		String outputNetwork = args[1];
		String targetCrs = args.length >= 3 ? args[2] : "EPSG:32643";
		String roadProfile = args.length >= 4 ? args[3] : "default";

		Path inputPath = Path.of(inputOsm);
		if (!Files.exists(inputPath)) {
			throw new IllegalArgumentException("OSM file not found: " + inputPath.toAbsolutePath());
		}

		Path outputPath = Path.of(outputNetwork);
		try {
			if (outputPath.getParent() != null) {
				Files.createDirectories(outputPath.getParent());
			}
		} catch (Exception e) {
			throw new RuntimeException("Cannot create output directory for: " + outputPath.toAbsolutePath(), e);
		}

		CoordinateTransformation transformation =
				TransformationFactory.getCoordinateTransformation(TransformationFactory.WGS84, targetCrs);

		String lowerName = inputPath.getFileName().toString().toLowerCase();
		Network network;
		if (lowerName.endsWith(".pbf")) {
			network = new SupersonicOsmNetworkReader.Builder()
					.setCoordinateTransformation(transformation)
					.build()
					.read(inputOsm);
		} else {
			// Fallback for .osm/.osm.gz XML sources.
			network = NetworkUtils.createNetwork();
			new OsmNetworkReader(network, transformation).parse(inputOsm);
		}

		new NetworkCleaner().run(network);
		applyLanePolicyFromOsm(inputPath, network);
		applySnRkCapacityPolicy(network, inputPath);
		applyRoadConditionProfile(network, roadProfile);
		applyTrafficSignalProxyFromOsm(inputPath, network, transformation);
		new NetworkWriter(network).write(outputPath.toString());

		System.out.println("Network created: " + outputPath.toAbsolutePath());
	}

	private static void applyLanePolicyFromOsm(Path inputOsm, Network network) {
		String fileName = inputOsm.getFileName().toString().toLowerCase();
		if (!(fileName.endsWith(".osm") || fileName.endsWith(".xml") || fileName.equals("map"))) {
			System.out.println("Lane policy from OSM tags skipped (unsupported format for parser): " + inputOsm);
			return;
		}

		Map<SegmentKey, Double> lanesByDirectedSegment = buildDirectedLaneMapFromOsmXml(inputOsm);
		if (lanesByDirectedSegment.isEmpty()) {
			System.out.println("Lane policy from OSM tags skipped (no road segments parsed).");
			return;
		}

		int matched = 0;
		int changed = 0;
		Set<String> changedLinkIds = new HashSet<>();

		for (Link link : network.getLinks().values()) {
			SegmentKey key = new SegmentKey(link.getFromNode().getId().toString(), link.getToNode().getId().toString());
			Double lanes = lanesByDirectedSegment.get(key);
			if (lanes == null) {
				continue;
			}
			matched++;
			if (Math.abs(link.getNumberOfLanes() - lanes) > 1e-9) {
				link.setNumberOfLanes(lanes);
				changed++;
				changedLinkIds.add(link.getId().toString());
			}
		}

		System.out.println("Lane policy applied from OSM tags/defaults:");
		System.out.println("  Directed segment rules parsed: " + lanesByDirectedSegment.size());
		System.out.println("  Network links matched: " + matched);
		System.out.println("  Network links with lane updates: " + changed);
	}

	/**
	 * Sets link {@code capacity} = (capacity per lane for OSM highway class) × {@link Link#getNumberOfLanes()},
	 * matching the report table (1000 / 300 / 100 veh/h per lane). Uses {@code origid} on links (OSM way id) when
	 * the input is OSM XML; otherwise falls back to free-speed class.
	 */
	private static void applySnRkCapacityPolicy(Network network, Path inputOsm) {
		Map<String, String> highwayByWayId = buildOsmWayIdToHighway(inputOsm);
		if (highwayByWayId.isEmpty()) {
			System.out.println("SN RK capacity policy: no OSM way→highway map (skip XML or empty); using free-speed fallback only.");
		}
		int updated = 0;
		for (Link link : network.getLinks().values()) {
			double perLane = resolveCapacityPerLaneVehPerHour(link, highwayByWayId);
			if (!Double.isFinite(perLane) || perLane <= 0) {
				continue;
			}
			double lanes = Math.max(1.0, link.getNumberOfLanes());
			double totalCap = perLane * lanes;
			if (Math.abs(totalCap - link.getCapacity()) > 1e-6) {
				link.setCapacity(totalCap);
				updated++;
			}
		}
		System.out.println("SN RK capacity policy applied: links updated=" + updated + " (per-lane caps: magistral="
			+ CAP_PER_LANE_MAGISTRAL_VEH_H + ", urban_arterial=" + CAP_PER_LANE_URBAN_ARTERIAL_VEH_H + ", local="
			+ CAP_PER_LANE_LOCAL_VEH_H + ")");
	}

	private static Map<String, String> buildOsmWayIdToHighway(Path inputOsm) {
		Map<String, String> out = new HashMap<>();
		String fileName = inputOsm.getFileName().toString().toLowerCase();
		if (!(fileName.endsWith(".osm") || fileName.endsWith(".xml") || fileName.equals("map"))) {
			return out;
		}
		DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
		dbf.setNamespaceAware(false);
		dbf.setExpandEntityReferences(false);
		Document doc;
		try {
			doc = dbf.newDocumentBuilder().parse(inputOsm.toFile());
		} catch (Exception e) {
			return out;
		}
		NodeList wayNodes = doc.getElementsByTagName("way");
		for (int i = 0; i < wayNodes.getLength(); i++) {
			Element way = (Element) wayNodes.item(i);
			String id = way.getAttribute("id");
			if (id == null || id.isBlank()) {
				continue;
			}
			Map<String, String> tags = readTags(way);
			String highway = tags.get("highway");
			if (highway == null || highway.isBlank() || !isRoadClassUsedForCar(highway)) {
				continue;
			}
			out.put(id.trim(), highway.trim());
		}
		return out;
	}

	private static double resolveCapacityPerLaneVehPerHour(Link link, Map<String, String> highwayByWayId) {
		Object orig = link.getAttributes().getAttribute("origid");
		if (orig != null) {
			String wayId = orig.toString().trim();
			String highway = highwayByWayId.get(wayId);
			if (highway != null) {
				Double c = capacityPerLaneForHighway(highway);
				if (c != null) {
					return c;
				}
			}
		}
		return capacityPerLaneFromFreespeedFallback(link.getFreespeed());
	}

	private static Double capacityPerLaneForHighway(String highway) {
		if (highway == null) {
			return null;
		}
		return switch (highway) {
			case "motorway", "motorway_link", "trunk", "trunk_link" -> CAP_PER_LANE_MAGISTRAL_VEH_H;
			case "primary", "primary_link", "secondary", "secondary_link" -> CAP_PER_LANE_URBAN_ARTERIAL_VEH_H;
			case "tertiary", "tertiary_link", "unclassified", "residential", "service", "living_street" -> CAP_PER_LANE_LOCAL_VEH_H;
			default -> null;
		};
	}

	/** When {@code origid} is missing (e.g. non-XML OSM source), map MATSim free speed to the same three capacity bands. */
	private static double capacityPerLaneFromFreespeedFallback(double freespeedMps) {
		SpeedClass sc = classifyByFreespeed(freespeedMps);
		return switch (sc) {
			case HIGHWAY -> CAP_PER_LANE_MAGISTRAL_VEH_H;
			case ARTERIAL, COLLECTOR -> CAP_PER_LANE_URBAN_ARTERIAL_VEH_H;
			case LOCAL -> CAP_PER_LANE_LOCAL_VEH_H;
		};
	}

	private static void applyRoadConditionProfile(Network network, String roadProfile) {
		String profile = roadProfile == null ? "default" : roadProfile.trim().toLowerCase();
		if (profile.equals("default")) {
			System.out.println("Road condition profile: default (no speed/capacity scaling).");
			return;
		}
		if (!profile.equals("poor")) {
			throw new IllegalArgumentException("Unknown roadProfile: " + roadProfile + " (allowed: default, poor)");
		}

		int changed = 0;
		for (Link link : network.getLinks().values()) {
			double fs = link.getFreespeed();
			SpeedClass speedClass = classifyByFreespeed(fs);
			double targetSpeedKmH;
			double capacityMultiplier;
			switch (speedClass) {
				case HIGHWAY -> {
					targetSpeedKmH = 70.0;
					capacityMultiplier = 0.85;
				}
				case ARTERIAL -> {
					targetSpeedKmH = 45.0;
					capacityMultiplier = 0.80;
				}
				case COLLECTOR -> {
					targetSpeedKmH = 30.0;
					capacityMultiplier = 0.75;
				}
				case LOCAL -> {
					targetSpeedKmH = 20.0;
					capacityMultiplier = 0.70;
				}
				default -> throw new IllegalStateException("Unexpected speed class: " + speedClass);
			}

			double newFs = targetSpeedKmH / 3.6;
			double newCap = Math.max(150.0, link.getCapacity() * capacityMultiplier);

			if (Math.abs(newFs - fs) > 1e-9 || Math.abs(newCap - link.getCapacity()) > 1e-9) {
				link.setFreespeed(newFs);
				link.setCapacity(newCap);
				changed++;
			}
		}

		System.out.println("Road condition profile applied: poor");
		System.out.println("  Links with updated speed/capacity: " + changed);
		System.out.println("  Target free-speeds (km/h): local=20, collector=30, arterial=45, highway=70");
	}

	private static void applyTrafficSignalProxyFromOsm(
		Path inputOsm,
		Network network,
		CoordinateTransformation transformation
	) {
		String fileName = inputOsm.getFileName().toString().toLowerCase();
		if (!(fileName.endsWith(".osm") || fileName.endsWith(".xml") || fileName.equals("map"))) {
			System.out.println("Traffic signal proxy skipped (unsupported OSM XML source format): " + inputOsm);
			return;
		}

		List<Coord> signalCoords = readOsmTrafficSignalCoords(inputOsm, transformation);
		if (signalCoords.isEmpty()) {
			System.out.println("Traffic signal proxy: no traffic_signals found in OSM; skipping.");
			return;
		}

		Set<String> touchedNodeIds = new HashSet<>();
		for (Coord sc : signalCoords) {
			Link nearest = NetworkUtils.getNearestLinkExactly(network, sc);
			if (nearest == null) {
				continue;
			}
			// Penalize both approaches adjacent to the signalized intersection (link endpoints).
			touchedNodeIds.add(nearest.getFromNode().getId().toString());
			touchedNodeIds.add(nearest.getToNode().getId().toString());
		}

		if (touchedNodeIds.isEmpty()) {
			System.out.println("Traffic signal proxy: signals found=" + signalCoords.size() + ", but no touched nodes mapped; skipping.");
			return;
		}

		int changed = 0;
		for (Link link : network.getLinks().values()) {
			String fromId = link.getFromNode().getId().toString();
			String toId = link.getToNode().getId().toString();
			if (!touchedNodeIds.contains(fromId) && !touchedNodeIds.contains(toId)) {
				continue;
			}
			// Apply only to car links.
			if (link.getAllowedModes() != null && !link.getAllowedModes().contains(TransportMode.car)) {
				continue;
			}
			double newFs = link.getFreespeed() * TRAFFIC_SIGNAL_FREESPEED_MULT;
			double newCap = link.getCapacity() * TRAFFIC_SIGNAL_CAPACITY_MULT;
			if (newFs > 0 && newCap > 0) {
				link.setFreespeed(newFs);
				link.setCapacity(newCap);
				changed++;
			}
		}

		System.out.println("Traffic signal proxy applied from OSM:");
		System.out.println("  traffic_signals found=" + signalCoords.size());
		System.out.println("  touched nodes=" + touchedNodeIds.size());
		System.out.println("  links updated=" + changed + " (mult: cap=" + TRAFFIC_SIGNAL_CAPACITY_MULT + ", fs=" + TRAFFIC_SIGNAL_FREESPEED_MULT + ")");
	}

	private static List<Coord> readOsmTrafficSignalCoords(Path inputOsm, CoordinateTransformation transformation) {
		List<Coord> out = new ArrayList<>();

		DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
		dbf.setNamespaceAware(false);
		dbf.setExpandEntityReferences(false);

		Document doc;
		try {
			doc = dbf.newDocumentBuilder().parse(inputOsm.toFile());
		} catch (Exception e) {
			System.out.println("Traffic signal proxy: failed to parse OSM XML: " + inputOsm.toAbsolutePath());
			return out;
		}

		NodeList nodeNodes = doc.getElementsByTagName("node");
		for (int i = 0; i < nodeNodes.getLength(); i++) {
			Element node = (Element) nodeNodes.item(i);
			String latS = node.getAttribute("lat");
			String lonS = node.getAttribute("lon");
			if (latS == null || lonS == null || latS.isBlank() || lonS.isBlank()) {
				continue;
			}

			Map<String, String> tags = readTags(node);
			String highway = tags.get("highway");
			String crossing = tags.get("crossing");
			boolean isSignal = "traffic_signals".equals(highway) || "traffic_signals".equals(crossing);
			if (!isSignal) {
				continue;
			}

			try {
				double lat = Double.parseDouble(latS);
				double lon = Double.parseDouble(lonS);
				out.add(transformation.transform(new Coord(lon, lat)));
			} catch (Exception ignored) {
				// skip malformed coords
			}
		}
		return out;
	}

	private static SpeedClass classifyByFreespeed(double freespeedMetersPerSecond) {
		if (freespeedMetersPerSecond >= 20.0) {
			return SpeedClass.HIGHWAY;
		}
		if (freespeedMetersPerSecond >= 12.0) {
			return SpeedClass.ARTERIAL;
		}
		if (freespeedMetersPerSecond >= 8.0) {
			return SpeedClass.COLLECTOR;
		}
		return SpeedClass.LOCAL;
	}

	private static Map<SegmentKey, Double> buildDirectedLaneMapFromOsmXml(Path inputOsm) {
		Map<SegmentKey, Double> out = new HashMap<>();

		DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
		dbf.setNamespaceAware(false);
		dbf.setExpandEntityReferences(false);

		Document doc;
		try {
			doc = dbf.newDocumentBuilder().parse(inputOsm.toFile());
		} catch (Exception e) {
			throw new RuntimeException("Failed to parse OSM XML for lane policy: " + inputOsm.toAbsolutePath(), e);
		}

		NodeList wayNodes = doc.getElementsByTagName("way");
		for (int i = 0; i < wayNodes.getLength(); i++) {
			Element way = (Element) wayNodes.item(i);
			Map<String, String> tags = readTags(way);
			String highway = tags.get("highway");
			if (highway == null || highway.isBlank()) {
				continue;
			}
			if (!isRoadClassUsedForCar(highway)) {
				continue;
			}

			boolean oneway = isOneway(tags.get("oneway"));
			int defaultPerDirection = defaultPerDirectionLanes(highway);
			int forwardLanes = computeForwardLanes(tags, oneway, defaultPerDirection);
			int backwardLanes = computeBackwardLanes(tags, oneway, defaultPerDirection);

			NodeList nds = way.getElementsByTagName("nd");
			if (nds.getLength() < 2) {
				continue;
			}
			for (int n = 0; n < nds.getLength() - 1; n++) {
				String from = ((Element) nds.item(n)).getAttribute("ref");
				String to = ((Element) nds.item(n + 1)).getAttribute("ref");
				if (from == null || from.isBlank() || to == null || to.isBlank()) {
					continue;
				}
				putMax(out, new SegmentKey(from, to), (double) forwardLanes);
				if (!oneway) {
					putMax(out, new SegmentKey(to, from), (double) backwardLanes);
				}
			}
		}
		return out;
	}

	private static Map<String, String> readTags(Element way) {
		Map<String, String> tags = new HashMap<>();
		NodeList tagNodes = way.getElementsByTagName("tag");
		for (int i = 0; i < tagNodes.getLength(); i++) {
			Element t = (Element) tagNodes.item(i);
			String k = t.getAttribute("k");
			String v = t.getAttribute("v");
			if (!k.isBlank()) {
				tags.put(k, v);
			}
		}
		return tags;
	}

	private static boolean isRoadClassUsedForCar(String highway) {
		return switch (highway) {
			case "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary",
					"secondary_link", "tertiary", "tertiary_link", "unclassified", "residential", "service", "living_street" -> true;
			default -> false;
		};
	}

	private static int defaultPerDirectionLanes(String highway) {
		// Defaults aligned with report table: magistral 4, urban arterial 2, local 2 (when OSM has no lanes tag).
		return switch (highway) {
			case "motorway", "motorway_link", "trunk", "trunk_link" -> 4;
			case "primary", "primary_link", "secondary", "secondary_link" -> 2;
			case "tertiary", "tertiary_link", "unclassified", "residential", "service", "living_street" -> 2;
			default -> 1;
		};
	}

	private static int computeForwardLanes(Map<String, String> tags, boolean oneway, int defaultPerDirection) {
		Integer lanesForward = parseLaneInt(tags.get("lanes:forward"));
		if (lanesForward != null) {
			return Math.max(1, lanesForward);
		}
		Integer lanes = parseLaneInt(tags.get("lanes"));
		if (lanes == null) {
			return defaultPerDirection;
		}
		if (oneway) {
			return Math.max(1, lanes);
		}
		return Math.max(1, lanes / 2);
	}

	private static int computeBackwardLanes(Map<String, String> tags, boolean oneway, int defaultPerDirection) {
		if (oneway) {
			return 0;
		}
		Integer lanesBackward = parseLaneInt(tags.get("lanes:backward"));
		if (lanesBackward != null) {
			return Math.max(1, lanesBackward);
		}
		Integer lanes = parseLaneInt(tags.get("lanes"));
		if (lanes == null) {
			return defaultPerDirection;
		}
		return Math.max(1, lanes / 2);
	}

	private static Integer parseLaneInt(String raw) {
		if (raw == null || raw.isBlank()) {
			return null;
		}
		StringBuilder sb = new StringBuilder();
		for (int i = 0; i < raw.length(); i++) {
			char c = raw.charAt(i);
			if (Character.isDigit(c)) {
				sb.append(c);
			} else if (sb.length() > 0) {
				break;
			}
		}
		if (sb.length() == 0) {
			return null;
		}
		try {
			return Integer.parseInt(sb.toString());
		} catch (NumberFormatException e) {
			return null;
		}
	}

	private static boolean isOneway(String raw) {
		if (raw == null) {
			return false;
		}
		String v = raw.trim().toLowerCase();
		return v.equals("yes") || v.equals("1") || v.equals("true");
	}

	private static void putMax(Map<SegmentKey, Double> map, SegmentKey key, double lanes) {
		Double prev = map.get(key);
		if (prev == null || lanes > prev) {
			map.put(key, lanes);
		}
	}

	private enum SpeedClass {
		HIGHWAY,
		ARTERIAL,
		COLLECTOR,
		LOCAL
	}

	private record SegmentKey(String fromNodeId, String toNodeId) {
	}
}
