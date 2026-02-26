package org.matsim.project;

import org.matsim.application.analysis.pt.PublicTransitAnalysis;
import org.matsim.application.prepare.network.CreateAvroNetwork;
import org.matsim.core.config.Config;
import org.matsim.simwrapper.Dashboard;
import org.matsim.simwrapper.DashboardProvider;
import org.matsim.simwrapper.Header;
import org.matsim.simwrapper.Layout;
import org.matsim.simwrapper.SimWrapper;
import org.matsim.simwrapper.viz.TransitViewer;

import java.util.ArrayList;
import java.util.List;

/**
 * Provides a PT dashboard variant that supports both compressed and uncompressed transit schedule outputs.
 */
public class ShamalganDashboardProvider implements DashboardProvider {

	@Override
	public List<Dashboard> getDashboards(Config config, SimWrapper simWrapper) {
		List<Dashboard> dashboards = new ArrayList<>();

		if (config.transit().isUseTransit()) {
			dashboards.add(new ShamalganPublicTransitDashboard());
		}

		return dashboards;
	}

	@Override
	public double priority() {
		// Higher than the default provider (-1), so this PT dashboard is added first.
		return 10.0;
	}

	/**
	 * PT dashboard tuned for Shamalgan runs: transit schedule glob matches both .xml and .xml.gz.
	 */
	public static final class ShamalganPublicTransitDashboard implements Dashboard {
		@Override
		public void configure(Header header, Layout layout) {
			header.title = "Public Transit";
			header.tab = "PT";
			header.triggerPattern = "(*.)?output_transitSchedule*xml*";

			layout.row("viewer").el(TransitViewer.class, (viz, data) -> {
				viz.title = "Transit Viewer";
				viz.height = 12d;
				viz.description = "Visualize the transit schedule.";

				// Include a network that has not been filtered by mode.
				viz.network = data.withContext("all").compute(CreateAvroNetwork.class, "network.avro",
						"--mode-filter", "", "--shp", "none");

				// Accept both output_transitSchedule.xml and output_transitSchedule.xml.gz
				viz.transitSchedule = data.output("(*.)?output_transitSchedule.xml*");
				viz.demand = data.compute(PublicTransitAnalysis.class, "pt_pax_volumes.csv.gz");
			});
		}
	}
}
