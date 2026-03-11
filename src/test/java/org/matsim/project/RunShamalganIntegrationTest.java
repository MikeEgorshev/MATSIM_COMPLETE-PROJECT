package org.matsim.project;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.RegisterExtension;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Population;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.population.PopulationUtils;
import org.matsim.testcases.MatsimTestUtils;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class RunShamalganIntegrationTest {

	@RegisterExtension
	final MatsimTestUtils utils = new MatsimTestUtils();

	@Test
	void runsTwoIterationsWithSampledPopulation() {
		Path testDir = Path.of(utils.getOutputDirectory()).toAbsolutePath();
		Path sampledPlans = testDir.resolve("population-sample.xml");
		createPopulationSample(
			Path.of("scenarios/shamalgan/population.xml"),
			sampledPlans,
			200
		);

		Config config = ConfigUtils.loadConfig("scenarios/shamalgan/config.xml");
		Path runOutput = testDir.resolve("run-output");
		config.controller().setOutputDirectory(runOutput.toString());
		config.controller().setLastIteration(2);
		config.global().setNumberOfThreads(1);
		config.qsim().setNumberOfThreads(1);
		config.plans().setInputFile(sampledPlans.toString());

		RunMatsim.run(config, false, false);

		assertThat(runOutput.resolve("output_config.xml")).exists();
		assertThat(runOutput.resolve("scorestats.csv")).exists();
		// config uses compressionType=gzip, so plans are written as .xml.gz
		assertThat(runOutput.resolve("output_plans.xml.gz")).exists();
		Path it2 = runOutput.resolve("ITERS").resolve("it.2");
		assertThat(it2.resolve("2.events.xml.gz")).exists();
	}

	private static void createPopulationSample(Path inputPlans, Path outputPlans, int personsToKeep) {
		Population fullPopulation = PopulationUtils.readPopulation(inputPlans.toString());
		Population sampledPopulation = PopulationUtils.createPopulation(ConfigUtils.createConfig());

		List<Person> persons = new ArrayList<>(fullPopulation.getPersons().values());
		int limit = Math.min(personsToKeep, persons.size());
		for (int i = 0; i < limit; i++) {
			sampledPopulation.addPerson(persons.get(i));
		}

		PopulationUtils.writePopulation(sampledPopulation, outputPlans.toString());
	}
}
