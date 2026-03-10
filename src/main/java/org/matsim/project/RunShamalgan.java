package org.matsim.project;

import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.simwrapper.SimWrapperConfigGroup;

import java.util.ArrayList;
import java.util.List;

public class RunShamalgan {
	private static final String THREADS_FLAG = "--threads";
	private static final String THREADS_PREFIX = "--threads=";
	private static final String GLOBAL_THREADS_OVERRIDE = "--config:global.numberOfThreads";
	private static final String QSIM_THREADS_OVERRIDE = "--config:qsim.numberOfThreads";
	private static final String ENV_THREADS = "MATSIM_THREADS";
	private static final String PREFER_LOCAL_DTD_PROPERTY = "matsim.preferLocalDtds";
	private static final int MAX_AUTO_THREADS = 16;

	public static void main(String[] args) {
		ensureStableXmlResolution();

		boolean enableOtfvis = false;
		boolean enableSimwrapper = false;
		Integer requestedThreads = null;
		List<String> configArgs = new ArrayList<>();

		if (args != null) {
			for (int i = 0; i < args.length; i++) {
				String arg = args[i];
				if ("--otfvis".equalsIgnoreCase(arg)) {
					enableOtfvis = true;
				} else if ("--simwrapper".equalsIgnoreCase(arg)) {
					enableSimwrapper = true;
				} else if (THREADS_FLAG.equalsIgnoreCase(arg)) {
					if (i + 1 >= args.length) {
						throw new IllegalArgumentException("--threads requires a positive integer value.");
					}
					requestedThreads = parseThreads(args[++i]);
				} else if (arg.toLowerCase().startsWith(THREADS_PREFIX)) {
					requestedThreads = parseThreads(arg.substring(THREADS_PREFIX.length()));
				} else {
					configArgs.add(arg);
				}
			}
		}

		if (configArgs.isEmpty()) {
			configArgs.add("scenarios/shamalgan/config.xml");
		}

		Config config = ConfigUtils.loadConfig(configArgs.toArray(new String[0]));
		applyThreadConfiguration(config, configArgs, requestedThreads);
		applySimwrapperConfiguration(config, enableSimwrapper);
		RunMatsim.run(config, enableOtfvis, enableSimwrapper);
	}

	private static void applySimwrapperConfiguration(Config config, boolean enableSimwrapper) {
		if (!enableSimwrapper) {
			return;
		}

		SimWrapperConfigGroup simwrapper = ConfigUtils.addOrGetModule(config, SimWrapperConfigGroup.class);
		simwrapper.setDefaultDashboards(SimWrapperConfigGroup.Mode.enabled);
		System.out.println("SimWrapper config: default dashboards enabled.");
	}

	private static void ensureStableXmlResolution() {
		String configured = System.getProperty(PREFER_LOCAL_DTD_PROPERTY);
		if (configured == null || configured.isBlank()) {
			System.setProperty(PREFER_LOCAL_DTD_PROPERTY, "true");
			System.out.println("XML config: matsim.preferLocalDtds=true (default).");
		} else {
			System.out.printf("XML config: matsim.preferLocalDtds=%s (from JVM property).%n", configured);
		}
	}

	private static void applyThreadConfiguration(Config config, List<String> configArgs, Integer requestedThreads) {
		Integer threadsFromEnv = requestedThreads == null ? parseThreadsFromEnv() : null;
		int threadsToUse = requestedThreads != null ? requestedThreads : (threadsFromEnv != null ? threadsFromEnv : recommendThreadCount());

		boolean hasGlobalOverride = hasConfigOverride(configArgs, GLOBAL_THREADS_OVERRIDE);
		boolean hasQsimOverride = hasConfigOverride(configArgs, QSIM_THREADS_OVERRIDE);

		if (!hasGlobalOverride) {
			config.global().setNumberOfThreads(threadsToUse);
		}
		if (!hasQsimOverride) {
			config.qsim().setNumberOfThreads(threadsToUse);
		}

		System.out.printf(
			"Thread config: availableProcessors=%d, global=%d%s, qsim=%d%s%n",
			Runtime.getRuntime().availableProcessors(),
			config.global().getNumberOfThreads(),
			hasGlobalOverride ? " (from config override)" : "",
			config.qsim().getNumberOfThreads(),
			hasQsimOverride ? " (from config override)" : ""
		);
	}

	private static boolean hasConfigOverride(List<String> configArgs, String key) {
		for (int i = 0; i < configArgs.size(); i++) {
			String arg = configArgs.get(i);
			if (arg.equalsIgnoreCase(key) || arg.toLowerCase().startsWith((key + "=").toLowerCase())) {
				return true;
			}
		}
		return false;
	}

	private static Integer parseThreadsFromEnv() {
		String value = System.getenv(ENV_THREADS);
		if (value == null || value.isBlank()) {
			return null;
		}
		return parseThreads(value.trim());
	}

	private static int recommendThreadCount() {
		int processors = Runtime.getRuntime().availableProcessors();
		int recommended = processors <= 2 ? processors : processors - 1;
		return Math.max(1, Math.min(MAX_AUTO_THREADS, recommended));
	}

	private static int parseThreads(String rawValue) {
		try {
			int parsed = Integer.parseInt(rawValue);
			if (parsed < 1) {
				throw new IllegalArgumentException("Thread count must be >= 1, got: " + rawValue);
			}
			return parsed;
		} catch (NumberFormatException e) {
			throw new IllegalArgumentException("Invalid thread count: " + rawValue, e);
		}
	}
}
