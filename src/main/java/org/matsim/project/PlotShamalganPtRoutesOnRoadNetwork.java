package org.matsim.project;

import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.Node;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.network.io.MatsimNetworkReader;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Set;

/**
 * Renders PT routes over road network as SVG and writes QA checks:
 * - each tagged stop is snapped to a real network link;
 * - each consecutive stop pair in a route has a directed shortest path on roads.
 */
public class PlotShamalganPtRoutesOnRoadNetwork {

	private static final int WIDTH = 1600;
	private static final int HEIGHT = 1100;
	private static final int PAD = 70;
	private static final double BOUNDS_MARGIN_M = 1500.0;
	private static final double SNAP_WARN_DIST_M = 80.0;
	private static final String[] COLORS = {
		"#00695C", "#C62828", "#1565C0", "#EF6C00", "#6A1B9A", "#2E7D32", "#283593", "#AD1457"
	};

	private record TaggedStopRow(String routeId, int stopSeq, String stopId, String name, double x, double y) {}
	private record StopOnRoad(TaggedStopRow src, Link snappedLink, double snapDistanceM) {}
	private record SegmentCheck(
		String routeId,
		int fromSeq,
		int toSeq,
		String fromStopId,
		String toStopId,
		boolean reachable,
		double networkDistanceM,
		double straightDistanceM,
		double detourFactor,
		List<Coord> pathCoords
	) {}
	private record Bounds(double minX, double maxX, double minY, double maxY) {}
	private record DijkstraResult(boolean reachable, double distanceM, List<Link> links) {}

	public static void main(String[] args) throws Exception {
		if (args.length < 5) {
			System.out.println(
				"Usage: PlotShamalganPtRoutesOnRoadNetwork <network.xml> <tagged_route_stops.csv> <out-map.svg> <out-stop-check.csv> <out-segment-check.csv> [out-summary.md]"
			);
			return;
		}

		Path networkFile = Path.of(args[0]);
		Path taggedCsv = Path.of(args[1]);
		Path outSvg = Path.of(args[2]);
		Path outStopCsv = Path.of(args[3]);
		Path outSegCsv = Path.of(args[4]);
		Path outSummary = args.length >= 6 ? Path.of(args[5]) : null;

		Network network = NetworkUtils.createNetwork();
		new MatsimNetworkReader(network).readFile(networkFile.toString());

		List<TaggedStopRow> rows = readTaggedStops(taggedCsv);
		if (rows.isEmpty()) {
			throw new IllegalStateException("No tagged rows found in " + taggedCsv.toAbsolutePath());
		}

		Map<String, List<TaggedStopRow>> byRoute = new HashMap<>();
		for (TaggedStopRow row : rows) {
			byRoute.computeIfAbsent(row.routeId, ignored -> new ArrayList<>()).add(row);
		}
		for (List<TaggedStopRow> routeRows : byRoute.values()) {
			routeRows.sort(Comparator.comparingInt(TaggedStopRow::stopSeq));
		}

		Map<String, StopOnRoad> stopMap = new HashMap<>();
		List<StopOnRoad> stopChecks = new ArrayList<>();
		for (TaggedStopRow row : rows) {
			StopOnRoad mapped = mapStopToLink(network, row);
			stopChecks.add(mapped);
			stopMap.put(row.stopId, mapped);
		}

		List<SegmentCheck> segmentChecks = new ArrayList<>();
		for (Map.Entry<String, List<TaggedStopRow>> entry : byRoute.entrySet()) {
			String routeId = entry.getKey();
			List<TaggedStopRow> ordered = closeLoopIfNeeded(entry.getValue());
			for (int i = 0; i < ordered.size() - 1; i++) {
				TaggedStopRow a = ordered.get(i);
				TaggedStopRow b = ordered.get(i + 1);
				segmentChecks.add(checkSegment(network, routeId, stopMap.get(a.stopId), stopMap.get(b.stopId)));
			}
		}

		Bounds bounds = buildBoundsFromStops(rows);
		Set<Id<Node>> nodesInWindow = collectNodesInWindow(network.getNodes().values(), bounds);
		String svg = renderSvg(network, byRoute, stopMap, segmentChecks, bounds, nodesInWindow);

		Files.createDirectories(outSvg.getParent());
		Files.createDirectories(outStopCsv.getParent());
		Files.createDirectories(outSegCsv.getParent());
		Files.writeString(outSvg, svg, StandardCharsets.UTF_8);
		writeStopChecksCsv(outStopCsv, stopChecks);
		writeSegmentChecksCsv(outSegCsv, segmentChecks);
		if (outSummary != null) {
			Files.createDirectories(outSummary.getParent());
			writeSummaryMd(outSummary, rows, byRoute, stopChecks, segmentChecks);
		}

		long snapWarnCount = stopChecks.stream().filter(s -> s.snapDistanceM > SNAP_WARN_DIST_M).count();
		long unreachable = segmentChecks.stream().filter(s -> !s.reachable).count();
		System.out.println("Saved map: " + outSvg.toAbsolutePath());
		System.out.println("Saved stop checks: " + outStopCsv.toAbsolutePath());
		System.out.println("Saved segment checks: " + outSegCsv.toAbsolutePath());
		if (outSummary != null) {
			System.out.println("Saved summary: " + outSummary.toAbsolutePath());
		}
		System.out.println("Routes: " + byRoute.size());
		System.out.println("Stops checked: " + stopChecks.size());
		System.out.println("Stop snaps > " + (int) SNAP_WARN_DIST_M + "m: " + snapWarnCount);
		System.out.println("Unreachable route segments: " + unreachable);
	}

	private static List<TaggedStopRow> readTaggedStops(Path csv) throws IOException {
		List<String> lines = Files.readAllLines(csv, StandardCharsets.UTF_8);
		if (lines.isEmpty()) return List.of();

		String[] header = lines.get(0).split(",", -1);
		int idxRoute = findIdx(header, "route_id");
		int idxSeq = findIdx(header, "stop_seq");
		int idxStopId = findIdx(header, "stop_id");
		int idxName = findIdx(header, "name");
		int idxX = findIdx(header, "x");
		int idxY = findIdx(header, "y");
		if (idxRoute < 0 || idxSeq < 0 || idxStopId < 0 || idxName < 0 || idxX < 0 || idxY < 0) {
			throw new IllegalArgumentException("Invalid tagged route CSV header in " + csv.toAbsolutePath());
		}

		List<TaggedStopRow> out = new ArrayList<>();
		for (int i = 1; i < lines.size(); i++) {
			String line = lines.get(i);
			if (line == null || line.isBlank()) continue;
			String[] p = line.split(",", -1);
			int req = Math.max(idxY, Math.max(idxX, Math.max(idxName, Math.max(idxStopId, Math.max(idxSeq, idxRoute)))));
			if (p.length <= req) continue;
			out.add(new TaggedStopRow(
				p[idxRoute].trim(),
				Integer.parseInt(p[idxSeq].trim()),
				p[idxStopId].trim(),
				p[idxName].trim(),
				Double.parseDouble(p[idxX].trim()),
				Double.parseDouble(p[idxY].trim())
			));
		}
		return out;
	}

	private static int findIdx(String[] header, String col) {
		for (int i = 0; i < header.length; i++) {
			if (col.equalsIgnoreCase(header[i].trim())) return i;
		}
		return -1;
	}

	private static StopOnRoad mapStopToLink(Network network, TaggedStopRow row) {
		Coord c = new Coord(row.x, row.y);
		Link link = NetworkUtils.getNearestLinkExactly(network, c);
		double dist = pointToSegmentDistance(c, link.getFromNode().getCoord(), link.getToNode().getCoord());
		return new StopOnRoad(row, link, dist);
	}

	private static List<TaggedStopRow> closeLoopIfNeeded(List<TaggedStopRow> ordered) {
		if (ordered.isEmpty()) return ordered;
		List<TaggedStopRow> out = new ArrayList<>(ordered);
		if (!out.get(0).stopId.equals(out.get(out.size() - 1).stopId)) {
			out.add(out.get(0));
		}
		return out;
	}

	private static SegmentCheck checkSegment(Network network, String routeId, StopOnRoad from, StopOnRoad to) {
		DijkstraResult core = shortestPathByLength(from.snappedLink.getToNode(), to.snappedLink.getFromNode());
		double straight = dist2d(new Coord(from.src.x, from.src.y), new Coord(to.src.x, to.src.y));

		List<Coord> geom = new ArrayList<>();
		geom.add(new Coord(from.src.x, from.src.y));
		geom.add(from.snappedLink.getToNode().getCoord());
		if (core.reachable) {
			for (Link link : core.links) {
				geom.add(link.getToNode().getCoord());
			}
		}
		geom.add(to.snappedLink.getFromNode().getCoord());
		geom.add(new Coord(to.src.x, to.src.y));

		double totalRoadDistance = from.snappedLink.getLength() + (core.reachable ? core.distanceM : Double.NaN) + to.snappedLink.getLength();
		double detour = (core.reachable && straight > 1e-6) ? (totalRoadDistance / straight) : Double.NaN;

		return new SegmentCheck(
			routeId,
			from.src.stopSeq,
			to.src.stopSeq,
			from.src.stopId,
			to.src.stopId,
			core.reachable,
			totalRoadDistance,
			straight,
			detour,
			geom
		);
	}

	private static DijkstraResult shortestPathByLength(Node start, Node goal) {
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

	private record NodeDist(Node node, double dist) {}

	private static Bounds buildBoundsFromStops(List<TaggedStopRow> rows) {
		double minX = Double.POSITIVE_INFINITY;
		double maxX = Double.NEGATIVE_INFINITY;
		double minY = Double.POSITIVE_INFINITY;
		double maxY = Double.NEGATIVE_INFINITY;
		for (TaggedStopRow r : rows) {
			minX = Math.min(minX, r.x);
			maxX = Math.max(maxX, r.x);
			minY = Math.min(minY, r.y);
			maxY = Math.max(maxY, r.y);
		}
		return new Bounds(minX - BOUNDS_MARGIN_M, maxX + BOUNDS_MARGIN_M, minY - BOUNDS_MARGIN_M, maxY + BOUNDS_MARGIN_M);
	}

	private static Set<Id<Node>> collectNodesInWindow(Collection<? extends Node> nodes, Bounds b) {
		Set<Id<Node>> out = new HashSet<>();
		for (Node n : nodes) {
			double x = n.getCoord().getX();
			double y = n.getCoord().getY();
			if (x >= b.minX && x <= b.maxX && y >= b.minY && y <= b.maxY) {
				out.add(n.getId());
			}
		}
		return out;
	}

	private static String renderSvg(
		Network network,
		Map<String, List<TaggedStopRow>> byRoute,
		Map<String, StopOnRoad> stopMap,
		List<SegmentCheck> segmentChecks,
		Bounds bounds,
		Set<Id<Node>> nodesInWindow
	) {
		StringBuilder s = new StringBuilder(1_000_000);
		s.append("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"").append(WIDTH).append("\" height=\"").append(HEIGHT)
			.append("\" viewBox=\"0 0 ").append(WIDTH).append(" ").append(HEIGHT).append("\">\n");
		s.append("<rect width=\"100%\" height=\"100%\" fill=\"#f8fafc\"/>\n");
		s.append("<text x=\"32\" y=\"36\" font-family=\"Segoe UI, Arial, sans-serif\" font-size=\"24\" fill=\"#111827\">Shamalgan PT routes on road network</text>\n");
		s.append("<text x=\"32\" y=\"58\" font-family=\"Segoe UI, Arial, sans-serif\" font-size=\"13\" fill=\"#4b5563\">Background: road links from network.xml | Foreground: route paths constrained to roads between ordered stops</text>\n");

		for (Link link : network.getLinks().values()) {
			if (!nodesInWindow.contains(link.getFromNode().getId()) || !nodesInWindow.contains(link.getToNode().getId())) continue;
			double x1 = sx(link.getFromNode().getCoord().getX(), bounds);
			double y1 = sy(link.getFromNode().getCoord().getY(), bounds);
			double x2 = sx(link.getToNode().getCoord().getX(), bounds);
			double y2 = sy(link.getToNode().getCoord().getY(), bounds);
			s.append("<line x1=\"").append(fmt(x1)).append("\" y1=\"").append(fmt(y1))
				.append("\" x2=\"").append(fmt(x2)).append("\" y2=\"").append(fmt(y2))
				.append("\" stroke=\"#cbd5e1\" stroke-width=\"1\" opacity=\"0.65\"/>\n");
		}

		Map<String, List<SegmentCheck>> segByRoute = new HashMap<>();
		for (SegmentCheck seg : segmentChecks) {
			segByRoute.computeIfAbsent(seg.routeId, ignored -> new ArrayList<>()).add(seg);
		}
		List<String> routeIds = new ArrayList<>(byRoute.keySet());
		Collections.sort(routeIds);

		for (int i = 0; i < routeIds.size(); i++) {
			String routeId = routeIds.get(i);
			String color = COLORS[i % COLORS.length];
			List<SegmentCheck> segs = segByRoute.getOrDefault(routeId, List.of());
			for (SegmentCheck seg : segs) {
				if (!seg.reachable || seg.pathCoords.size() < 2) continue;
				s.append("<polyline points=\"");
				for (Coord c : seg.pathCoords) {
					s.append(fmt(sx(c.getX(), bounds))).append(",").append(fmt(sy(c.getY(), bounds))).append(" ");
				}
				s.append("\" fill=\"none\" stroke=\"").append(color).append("\" stroke-width=\"3.2\" opacity=\"0.9\" stroke-linecap=\"round\" stroke-linejoin=\"round\"/>\n");
			}
		}

		for (int i = 0; i < routeIds.size(); i++) {
			String routeId = routeIds.get(i);
			String color = COLORS[i % COLORS.length];
			for (TaggedStopRow row : byRoute.get(routeId)) {
				double x = sx(row.x, bounds);
				double y = sy(row.y, bounds);
				s.append("<circle cx=\"").append(fmt(x)).append("\" cy=\"").append(fmt(y))
					.append("\" r=\"3.6\" fill=\"").append(color).append("\" stroke=\"#ffffff\" stroke-width=\"1.1\"/>\n");
			}
		}

		int baseX = 32;
		int baseY = 86;
		for (int i = 0; i < routeIds.size(); i++) {
			String routeId = routeIds.get(i);
			String color = COLORS[i % COLORS.length];
			int x = baseX + (i % 2) * 320;
			int y = baseY + (i / 2) * 22;
			long stopCount = byRoute.get(routeId).size();
			long badSegs = segmentChecks.stream().filter(seg -> seg.routeId.equals(routeId) && !seg.reachable).count();
			s.append("<line x1=\"").append(x).append("\" y1=\"").append(y).append("\" x2=\"").append(x + 24).append("\" y2=\"").append(y)
				.append("\" stroke=\"").append(color).append("\" stroke-width=\"4\"/>\n");
			s.append("<text x=\"").append(x + 30).append("\" y=\"").append(y + 4)
				.append("\" font-family=\"Segoe UI, Arial, sans-serif\" font-size=\"12\" fill=\"#111827\">route ")
				.append(routeId).append(" (").append(stopCount).append(" stops, ").append(badSegs).append(" unreachable segs)</text>\n");
		}

		long snapWarn = stopMap.values().stream().filter(v -> v.snapDistanceM > SNAP_WARN_DIST_M).count();
		long unreach = segmentChecks.stream().filter(seg -> !seg.reachable).count();
		s.append("<rect x=\"1060\" y=\"18\" width=\"520\" height=\"84\" rx=\"8\" fill=\"#ffffff\" stroke=\"#d1d5db\"/>\n");
		s.append("<text x=\"1080\" y=\"45\" font-family=\"Segoe UI, Arial, sans-serif\" font-size=\"13\" fill=\"#111827\">QA: stop snap warning threshold = ")
			.append((int) SNAP_WARN_DIST_M).append(" m</text>\n");
		s.append("<text x=\"1080\" y=\"66\" font-family=\"Segoe UI, Arial, sans-serif\" font-size=\"13\" fill=\"#111827\">Stops above threshold: ")
			.append(snapWarn).append("</text>\n");
		s.append("<text x=\"1080\" y=\"87\" font-family=\"Segoe UI, Arial, sans-serif\" font-size=\"13\" fill=\"#111827\">Unreachable route segments: ")
			.append(unreach).append("</text>\n");
		s.append("</svg>\n");
		return s.toString();
	}

	private static void writeStopChecksCsv(Path out, List<StopOnRoad> rows) throws IOException {
		try (BufferedWriter w = Files.newBufferedWriter(out, StandardCharsets.UTF_8)) {
			w.write("route_id,stop_seq,stop_id,name,x,y,snapped_link_id,snap_distance_m\n");
			rows.sort(Comparator.comparing((StopOnRoad s) -> s.src.routeId).thenComparingInt(s -> s.src.stopSeq));
			for (StopOnRoad r : rows) {
				w.write(csv(r.src.routeId) + "," + r.src.stopSeq + "," + csv(r.src.stopId) + "," + csv(r.src.name) + ","
					+ fmt(r.src.x) + "," + fmt(r.src.y) + "," + csv(r.snappedLink.getId().toString()) + "," + fmt(r.snapDistanceM) + "\n");
			}
		}
	}

	private static void writeSegmentChecksCsv(Path out, List<SegmentCheck> rows) throws IOException {
		try (BufferedWriter w = Files.newBufferedWriter(out, StandardCharsets.UTF_8)) {
			w.write("route_id,from_seq,to_seq,from_stop_id,to_stop_id,reachable,network_distance_m,straight_distance_m,detour_factor\n");
			rows.sort(Comparator.comparing((SegmentCheck s) -> s.routeId).thenComparingInt(s -> s.fromSeq));
			for (SegmentCheck r : rows) {
				w.write(csv(r.routeId) + "," + r.fromSeq + "," + r.toSeq + "," + csv(r.fromStopId) + "," + csv(r.toStopId) + ","
					+ r.reachable + "," + fmt(r.networkDistanceM) + "," + fmt(r.straightDistanceM) + "," + fmt(r.detourFactor) + "\n");
			}
		}
	}

	private static void writeSummaryMd(
		Path out,
		List<TaggedStopRow> rows,
		Map<String, List<TaggedStopRow>> byRoute,
		List<StopOnRoad> stopChecks,
		List<SegmentCheck> segmentChecks
	) throws IOException {
		long snapWarn = stopChecks.stream().filter(s -> s.snapDistanceM > SNAP_WARN_DIST_M).count();
		double maxSnap = stopChecks.stream().mapToDouble(s -> s.snapDistanceM).max().orElse(Double.NaN);
		long unreach = segmentChecks.stream().filter(s -> !s.reachable).count();

		StringBuilder md = new StringBuilder();
		md.append("# PT Route On-Road QA\n\n");
		md.append("- Routes: ").append(byRoute.size()).append("\n");
		md.append("- Tagged stop rows: ").append(rows.size()).append("\n");
		md.append("- Stops with snap distance > ").append((int) SNAP_WARN_DIST_M).append(" m: ").append(snapWarn).append("\n");
		md.append("- Max snap distance [m]: ").append(fmt(maxSnap)).append("\n");
		md.append("- Unreachable consecutive stop segments: ").append(unreach).append("\n\n");
		md.append("## Interpretation\n\n");
		md.append("- `snap_distance_m` checks how far the tagged point is from the snapped road link geometry.\n");
		md.append("- `reachable=false` means the directed road network has no path from one stop segment to the next.\n");
		md.append("- PT route drawing in SVG follows road links from this check (not straight lines).\n");
		Files.writeString(out, md.toString(), StandardCharsets.UTF_8);
	}

	private static String csv(String s) {
		String safe = s == null ? "" : s;
		if (safe.contains(",") || safe.contains("\"")) {
			return "\"" + safe.replace("\"", "\"\"") + "\"";
		}
		return safe;
	}

	private static double sx(double x, Bounds b) {
		double denom = Math.max(1e-9, b.maxX - b.minX);
		return PAD + ((x - b.minX) * (WIDTH - 2.0 * PAD) / denom);
	}

	private static double sy(double y, Bounds b) {
		double denom = Math.max(1e-9, b.maxY - b.minY);
		return HEIGHT - PAD - ((y - b.minY) * (HEIGHT - 2.0 * PAD) / denom);
	}

	private static String fmt(double v) {
		if (!Double.isFinite(v)) return "";
		return String.format(Locale.ROOT, "%.3f", v);
	}

	private static double dist2d(Coord a, Coord b) {
		double dx = a.getX() - b.getX();
		double dy = a.getY() - b.getY();
		return Math.sqrt(dx * dx + dy * dy);
	}

	private static double pointToSegmentDistance(Coord p, Coord a, Coord b) {
		double px = p.getX();
		double py = p.getY();
		double ax = a.getX();
		double ay = a.getY();
		double bx = b.getX();
		double by = b.getY();
		double abx = bx - ax;
		double aby = by - ay;
		double apx = px - ax;
		double apy = py - ay;
		double ab2 = abx * abx + aby * aby;
		if (ab2 <= 1e-12) {
			double dx = px - ax;
			double dy = py - ay;
			return Math.sqrt(dx * dx + dy * dy);
		}
		double t = (apx * abx + apy * aby) / ab2;
		t = Math.max(0.0, Math.min(1.0, t));
		double cx = ax + t * abx;
		double cy = ay + t * aby;
		double dx = px - cx;
		double dy = py - cy;
		return Math.sqrt(dx * dx + dy * dy);
	}
}
