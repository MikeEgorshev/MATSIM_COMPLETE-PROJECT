package org.matsim.project;

import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.NetworkWriter;
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
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class PrepareShamalganNetwork {

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
		applyRoadConditionProfile(network, roadProfile);
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
		return switch (highway) {
			case "motorway", "motorway_link", "trunk", "trunk_link" -> 2;
			case "primary", "primary_link", "secondary", "secondary_link" -> 1;
			case "tertiary", "tertiary_link", "unclassified", "residential", "service", "living_street" -> 1;
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
