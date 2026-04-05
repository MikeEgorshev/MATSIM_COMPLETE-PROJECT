/* *********************************************************************** *
 * project: org.matsim.*												   *
 *                                                                         *
 * *********************************************************************** *
 *                                                                         *
 * copyright       : (C) 2008 by the members listed in the COPYING,        *
 *                   LICENSE and WARRANTY file.                            *
 * email           : info at matsim dot org                                *
 *                                                                         *
 * *********************************************************************** *
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *   See also COPYING, LICENSE and WARRANTY file                           *
 *                                                                         *
 * *********************************************************************** */
package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.api.core.v01.network.Link;
import org.matsim.contrib.otfvis.OTFVisLiveModule;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.config.groups.ControllerConfigGroup;
import org.matsim.core.controler.Controler;
import org.matsim.core.controler.OutputDirectoryHierarchy.OverwriteFileSetting;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.simwrapper.SimWrapperModule;
import org.matsim.api.core.v01.population.Activity;
import org.matsim.api.core.v01.population.PlanElement;
import org.matsim.api.core.v01.population.Plan;
import org.matsim.api.core.v01.population.Person;
import org.matsim.api.core.v01.population.Leg;
import org.matsim.core.scoring.ScoringFunction;
import org.matsim.core.scoring.SumScoringFunction;
import org.matsim.core.scoring.functions.CharyparNagelScoringFunctionFactory;

/**
 * @author nagel
 *
 */
public class RunMatsim{

	/**
	 * Additional penalty for walk legs longer than {@link #WALK_PENALTY_THRESHOLD_M}.
	 * This is intentionally piecewise (thresholded) to avoid making short access walks too expensive.
	 */
	private static final double WALK_PENALTY_THRESHOLD_M = 1_000.0;
	private static final double WALK_PENALTY_UTIL_PER_M_BEYOND_THRESHOLD = -0.001; // -1.0 util per extra km

	public static void main(String[] args) {

		Config config;
		if ( args==null || args.length==0 || args[0]==null ){
			config = ConfigUtils.loadConfig( "scenarios/equil/config.xml" );
		} else {
			config = ConfigUtils.loadConfig( args );
		}

		run(config, false, false);
	}

	public static void run(Config config) {
		run(config, false, false);
	}

	public static void run(Config config, boolean enableOtfvis, boolean enableSimwrapper) {

		config.controller().setOverwriteFileSetting( OverwriteFileSetting.deleteDirectoryIfExists );

		// possibly modify config here

		// ---
		
		Scenario scenario = ScenarioUtils.loadScenario(config) ;
		fillMissingActivityCoordsFromLinks(scenario);

		// possibly modify scenario here
		
		// ---
		
		Controler controler = new Controler( scenario ) ;
		
		// possibly modify controler here
		installWalkDistancePenaltyScoring(controler, scenario);

		if (enableOtfvis) {
			controler.addOverridingModule(new OTFVisLiveModule());
		}
		if (enableSimwrapper) {
			controler.addOverridingModule(new SimWrapperModule());
		}
		
		// ---
		
		controler.run();
	}

	private static void installWalkDistancePenaltyScoring(Controler controler, Scenario scenario) {
		CharyparNagelScoringFunctionFactory baseFactory = new CharyparNagelScoringFunctionFactory(scenario);
		double brainExpBeta = scenario.getConfig().scoring().getBrainExpBeta();

		controler.setScoringFunctionFactory(person -> {
			ScoringFunction base = baseFactory.createNewScoringFunction(person);
			WalkDistancePenaltyScoring penalty = new WalkDistancePenaltyScoring(brainExpBeta);

			if (base instanceof SumScoringFunction sum) {
				sum.addScoringFunction(penalty);
				return sum;
			}

			throw new IllegalStateException("Expected SumScoringFunction from CharyparNagelScoringFunctionFactory, got: " + base.getClass().getName());
		});
	}

	private static final class WalkDistancePenaltyScoring implements SumScoringFunction.BasicScoring, SumScoringFunction.LegScoring {
		private final double brainExpBeta;
		private double score = 0.0;

		private WalkDistancePenaltyScoring(double brainExpBeta) {
			this.brainExpBeta = brainExpBeta;
		}

		@Override
		public void handleLeg(Leg leg) {
			if (leg == null || leg.getMode() == null || !TransportMode.walk.equals(leg.getMode())) {
				return;
			}
			if (leg.getRoute() == null) {
				return;
			}
			double distM = leg.getRoute().getDistance();
			if (!Double.isFinite(distM) || distM <= WALK_PENALTY_THRESHOLD_M) {
				return;
			}
			double beyond = distM - WALK_PENALTY_THRESHOLD_M;
			score += beyond * WALK_PENALTY_UTIL_PER_M_BEYOND_THRESHOLD * brainExpBeta;
		}

		@Override
		public void finish() {
			// no-op
		}

		@Override
		public double getScore() {
			return score;
		}
	}

	private static void fillMissingActivityCoordsFromLinks(Scenario scenario) {
		int fixed = 0;
		for (Person person : scenario.getPopulation().getPersons().values()) {
			for (Plan plan : person.getPlans()) {
				for (PlanElement pe : plan.getPlanElements()) {
					if (pe instanceof Activity act && act.getCoord() == null && act.getLinkId() != null) {
						Link link = scenario.getNetwork().getLinks().get(act.getLinkId());
						if (link != null && link.getCoord() != null) {
							act.setCoord(link.getCoord());
							fixed++;
						}
					}
				}
			}
		}
		System.out.println("Filled missing activity coords from links: " + fixed);
	}
	
}
