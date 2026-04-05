package org.matsim.project;

import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.Node;
import org.matsim.api.core.v01.population.Activity;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.Population;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.population.PopulationUtils;
import org.matsim.core.scenario.ScenarioUtils;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Optional zonal population generator.
 *
 * Input zones CSV format is documented in original-input-data/shamalgan/zones-template.csv.
 * This class is intentionally simple and heavily parameterized for easy editing.
 */
public class PrepareShamalganPopulationFromZones {

	// =========================
	// USER SETTINGS (edit here)
	// =========================
	private static final int AGENT_COUNT = 5000;
	private static final double EMPLOYED_SHARE = 0.65;
	private static final double CAR_MODE_SHARE = 0.55;
	private static final double PT_MODE_SHARE = 0.25;
	private static final long RANDOM_SEED = 20260217L;
	private static final double PLACEMENT_RADIUS_M = 300.0;

	public static void main(String[] args) throws Exception {
		if (args.length < 3) {
			System.out.println("Usage:");
			System.out.println("  PrepareShamalganPopulationFromZones <input-network.xml> <zones.csv> <output-population.xml> [agentCount]");
			System.out.println("Example:");
			System.out.println("  PrepareShamalganPopulationFromZones scenarios/shamalgan/network.xml original-input-data/shamalgan/zones-derived.csv scenarios/shamalgan/population.xml");
			return;
		}

		String networkFile = args[0];
		String zonesFile = args[1];
		String populationOut = args[2];
		Path networkPath = Path.of(networkFile);
		Path zonesPath = Path.of(zonesFile);
		if (!Files.exists(networkPath)) {
			throw new IllegalArgumentException("Network file not found: " + networkPath.toAbsolutePath());
		}
		if (!Files.exists(zonesPath)) {
			throw new IllegalArgumentException("Zones CSV not found: " + zonesPath.toAbsolutePath());
		}

		List<ZoneSpec> zones = readZones(zonesPath.toString());
		if (zones.isEmpty()) {
			throw new IllegalStateException("No zones loaded from: " + zonesFile);
		}
		int inferredAgents = inferAgentCount(zones);
		int agentCount = args.length >= 4 ? Integer.parseInt(args[3]) : inferredAgents;

		Config config = ConfigUtils.createConfig();
		config.network().setInputFile(networkPath.toString());
		Scenario scenario = ScenarioUtils.loadScenario(config);
		Network network = scenario.getNetwork();
		Population population = scenario.getPopulation();

		SplittableRandom rnd = new SplittableRandom(RANDOM_SEED);
		for (int i = 0; i < agentCount; i++) {
			ZoneSpec homeZone = weightedSample(zones, rnd, true);
			ZoneSpec workZone = weightedSample(zones, rnd, false);
			boolean employed = rnd.nextDouble() < EMPLOYED_SHARE;
			String mode = drawMode(rnd);

			Coord homeCoord;
			Link homeLink;
			CoordAndLink homeWeighted = coordAndLinkWeightedByLength(homeZone.homeX, homeZone.homeY, PLACEMENT_RADIUS_M, network, rnd);
			if (homeWeighted != null) {
				homeCoord = homeWeighted.coord;
				homeLink = homeWeighted.link;
			} else {
				homeCoord = jitter(homeZone.homeX, homeZone.homeY, PLACEMENT_RADIUS_M, rnd);
				homeLink = NetworkUtils.getNearestLinkExactly(network, homeCoord);
			}

			Coord workCoord;
			Link actLink;
			CoordAndLink workWeighted = coordAndLinkWeightedByLength(workZone.workX, workZone.workY, PLACEMENT_RADIUS_M, network, rnd);
			if (workWeighted != null) {
				workCoord = workWeighted.coord;
				actLink = workWeighted.link;
			} else {
				workCoord = jitter(workZone.workX, workZone.workY, PLACEMENT_RADIUS_M, rnd);
				actLink = NetworkUtils.getNearestLinkExactly(network, workCoord);
			}

			Person person = population.getFactory().createPerson(Id.createPersonId("zone_" + i));
			Plan plan = population.getFactory().createPlan();

			Activity home1 = PopulationUtils.createActivityFromLinkId("home", homeLink.getId());
			if (employed) {
				home1.setEndTime(7 * 3600 + rnd.nextInt(2 * 3600));
				plan.addActivity(home1);
				plan.addLeg(PopulationUtils.createLeg(mode));

				Activity work = PopulationUtils.createActivityFromLinkId("work", actLink.getId());
				work.setEndTime(16 * 3600 + rnd.nextInt(3 * 3600));
				plan.addActivity(work);
			} else {
				home1.setEndTime(10 * 3600 + rnd.nextInt(5 * 3600));
				plan.addActivity(home1);
				plan.addLeg(PopulationUtils.createLeg(mode));

				Activity other = PopulationUtils.createActivityFromLinkId("other", actLink.getId());
				other.setEndTime(12 * 3600 + rnd.nextInt(8 * 3600));
				plan.addActivity(other);
			}

			plan.addLeg(PopulationUtils.createLeg(mode));
			Activity home2 = PopulationUtils.createActivityFromLinkId("home", homeLink.getId());
			plan.addActivity(home2);

			person.addPlan(plan);
			population.addPerson(person);
		}

		Path out = Path.of(populationOut);
		if (out.getParent() != null) {
			Files.createDirectories(out.getParent());
		}

		PopulationUtils.writePopulation(population, out.toString());
		System.out.println("Population created from zones: " + out.toAbsolutePath() + " (agents=" + agentCount + ", inferred=" + inferredAgents + ")");
	}

	private static int inferAgentCount(List<ZoneSpec> zones) {
		double sum = 0.0;
		for (ZoneSpec z : zones) {
			sum += z.homeWeight;
		}
		// Keep reasonable bounds for interactive runs.
		int rounded = (int) Math.round(sum);
		return Math.max(500, Math.min(100_000, rounded));
	}

	private static List<ZoneSpec> readZones(String zonesFile) throws Exception {
		List<ZoneSpec> zones = new ArrayList<>();
		List<String> lines = Files.readAllLines(Path.of(zonesFile));
		for (String line : lines) {
			if (line == null || line.isBlank() || line.startsWith("zone_id")) {
				continue;
			}
			String[] p = line.split(",");
			if (p.length < 7) {
				continue;
			}
			zones.add(new ZoneSpec(
					p[0].trim(),
					Double.parseDouble(p[1].trim()),
					Double.parseDouble(p[2].trim()),
					Double.parseDouble(p[3].trim()),
					Double.parseDouble(p[4].trim()),
					Double.parseDouble(p[5].trim()),
					Double.parseDouble(p[6].trim())
			));
		}
		return zones;
	}

	private static ZoneSpec weightedSample(List<ZoneSpec> zones, SplittableRandom rnd, boolean home) {
		double sum = 0.0;
		for (ZoneSpec z : zones) {
			sum += home ? z.homeWeight : z.workWeight;
		}
		if (sum <= 0) {
			return zones.get(rnd.nextInt(zones.size()));
		}

		double target = rnd.nextDouble() * sum;
		double c = 0.0;
		for (ZoneSpec z : zones) {
			c += home ? z.homeWeight : z.workWeight;
			if (c >= target) {
				return z;
			}
		}
		return zones.get(zones.size() - 1);
	}

	private static String drawMode(SplittableRandom rnd) {
		double x = rnd.nextDouble();
		if (x < CAR_MODE_SHARE) return TransportMode.car;
		if (x < CAR_MODE_SHARE + PT_MODE_SHARE) return TransportMode.pt;
		return TransportMode.walk;
	}

	private static Coord jitter(double x, double y, double stdM, SplittableRandom rnd) {
		double jx = x + gaussianApprox(rnd) * stdM;
		double jy = y + gaussianApprox(rnd) * stdM;
		return new Coord(jx, jy);
	}

	private static double gaussianApprox(SplittableRandom rnd) {
		double sum = 0;
		for (int i = 0; i < 12; i++) {
			sum += rnd.nextDouble();
		}
		return sum - 6.0;
	}

	/**
	 * Length-weighted placement within a radius: select a link within radius proportionally to its length,
	 * then a random point on that link. Returns null if no links within radius (caller should fallback to jitter + nearest link).
	 */
	private static CoordAndLink coordAndLinkWeightedByLength(double zoneX, double zoneY, double radiusM, Network network, SplittableRandom rnd) {
		List<Link> inRadius = new ArrayList<>();
		List<Double> weights = new ArrayList<>();
		for (Link link : network.getLinks().values()) {
			Node from = link.getFromNode();
			Node to = link.getToNode();
			double x1 = from.getCoord().getX();
			double y1 = from.getCoord().getY();
			double x2 = to.getCoord().getX();
			double y2 = to.getCoord().getY();
			double dist = distancePointToSegment(zoneX, zoneY, x1, y1, x2, y2);
			if (dist <= radiusM) {
				inRadius.add(link);
				weights.add(link.getLength());
			}
		}
		if (inRadius.isEmpty()) {
			return null;
		}
		double sumWeight = 0.0;
		for (Double w : weights) {
			sumWeight += w;
		}
		if (sumWeight <= 0.0) {
			return null;
		}
		double target = rnd.nextDouble() * sumWeight;
		double cum = 0.0;
		Link chosen = inRadius.get(0);
		for (int j = 0; j < inRadius.size(); j++) {
			cum += weights.get(j);
			if (cum >= target) {
				chosen = inRadius.get(j);
				break;
			}
		}
		// Random point on segment
		Node from = chosen.getFromNode();
		Node to = chosen.getToNode();
		double x1 = from.getCoord().getX();
		double y1 = from.getCoord().getY();
		double x2 = to.getCoord().getX();
		double y2 = to.getCoord().getY();
		double t = rnd.nextDouble();
		double cx = x1 + t * (x2 - x1);
		double cy = y1 + t * (y2 - y1);
		return new CoordAndLink(new Coord(cx, cy), chosen);
	}

	private static double distancePointToSegment(double px, double py, double x1, double y1, double x2, double y2) {
		double dx = x2 - x1;
		double dy = y2 - y1;
		double len2 = dx * dx + dy * dy;
		if (len2 < 1e-20) {
			return Math.hypot(px - x1, py - y1);
		}
		double t = ((px - x1) * dx + (py - y1) * dy) / len2;
		t = Math.max(0.0, Math.min(1.0, t));
		double qx = x1 + t * dx;
		double qy = y1 + t * dy;
		return Math.hypot(px - qx, py - qy);
	}

	private record CoordAndLink(Coord coord, Link link) {
	}

	private record ZoneSpec(
			String zoneId,
			double homeX,
			double homeY,
			double homeWeight,
			double workX,
			double workY,
			double workWeight
	) {
	}
}
