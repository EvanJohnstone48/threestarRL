## threestarRL Project Idea

threestarRL is a research project that builds a Clash of Clans attack simulator, called "The Sandbox", and uses it as a reinforcement learning environment to study whether an agent can learn base attacking strategy through repeated simulated attacks ( and hopfully get some 3 stars :).

## Project premise

The goal is to train a reinforcement learning agent to attack a base in a simplified Clash-style environment. This is not meant to interact with the real game, automate gameplay, or function as a live bot. The project is a research system built around a custom simulator that has similar strategic structure: base layouts, grid-based buildings, walls, troops, defenses, pathfinding, deployment decisions, and attack scoring.

The core research question is:

Can an RL agent learn useful attack strategy, such as deployment timing, troop placement, pathing awareness, spell usage, and target prioritization, inside a custom base-attack simulator?

## Main project components

The project has three major parts.

1. The Sandbox  
   A custom Clash-style simulator where bases can be built, attacked, visualized, and replayed.

2. Base extraction  
   A future computer vision pipeline that turns an image of a base into a structured grid representation.

3. RL training  
   A reinforcement learning environment built on top of The Sandbox, where agents learn to attack bases through simulation.

## The Sandbox

The Sandbox is the simulator layer of the project.

It should support:

- An isometric grid similar to Clash-style base layouts
- Manual building placement
- Wall placement
- Building sizes based on tile dimensions
- Custom sprites and assets loaded from local folders
- Troop deployment
- Defense targeting
- Building health
- Troop health
- Movement and pathfinding
- Attack timing
- Attack scoring
- Replay logging
- Eventually, RL-compatible reset and step functions

The Sandbox should not start as a full game clone. It should start as a deterministic simulator core with a visual interface built around it.

The simulator core should be separate from the renderer.

The core owns the game state.

The frontend only displays the state.

This matters because RL training needs a fast, headless environment. The model should be able to run thousands or millions of simulation steps without needing animations, sprites, or a browser window.

## Suggested architecture

```text
siege-mind/
    sandbox-core/
        Pure simulator logic
        Grid system
        Buildings
        Troops
        Defenses
        Combat
        Pathfinding
        Attack scoring
        Replay data

    sandbox-web/
        Visual editor
        Isometric grid renderer
        Manual base builder
        Manual attack tester
        Replay viewer

    sandbox-env/
        RL environment wrapper
        Observation builder
        Action parser
        Reward functions
        Curriculum configs

    data/
        buildings.json
        troops.json
        spells.json
        sample_bases/
        th6_rules.json

    experiments/
        Training scripts
        Evaluation scripts
        Saved models
        Logs
        Plots

    docs/
        idea.md
        simulator_design.md
        rl_plan.md
        assumptions.md