## threestarRL Project Idea

threestarRL is a research project that builds a Clash of Clans attack simulator, called "The Sandbox", and uses it as a reinforcement learning environment to study whether an agent can learn base attacking strategy through repeated simulated attacks ( and hopfully get some 3 stars :).

## Project premise

The goal is to train a reinforcement learning agent to attack a base in a Clash-style environment. The project is a research system built around a custom simulator that simulates clash's strategic structure: base layouts, grid-based buildings, walls, troops, defenses, pathfinding, deployment decisions, and attack scoring.

The core research question is:

Can an RL agent learn useful attack strategy, such as deployment timing, troop placement, pathing awareness, spell usage, and target prioritization, inside a custom base-attack simulator?

## Main project components

The project has three major parts.

1. The Sandbox  
   A custom Clash-style simulator where bases can be built, attacked, visualized, and maybe replayed.

2. The Cartographer 
   A future computer vision pipeline that turns an image of a base into a structured grid representation.

3. The Barracks  
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
- More that I haven't figured out yet

The Sandbox should start as a deterministic simulator core with a visual interface built around it. For the start of the project we will only be using troops and buildings up to town hall 6 in the game. The rest can come later as we want to scale it.

The simulator core should be separate from the renderer.

The core owns the game state.

The frontend only displays the state.

Since the RL training needs a fast, headless environment. 

## Suggested architecture

Important: this is just the suggested architecture, you can make it however you want for the deepest modules and cleanest codebase.

```text
threestarRL/
    .claude/
        claude stuff

    app/
        docs/
            all documentation for different parts of the project to be referenced by the AI:
            three folders for the major parts, each will have PRDs and other documentation as we build it out in the future
            idea.md: initial idea you are reading now
            agent.md: explains the process I will be using to agentically grow this codebase
            ubiquitous-language.md: a glossary for terms used in this coding project
            technical.md: the technical stack and implementation used for this project
            roadmap.md: the implementation plan for the project

            sandbox/
                The Sandbox PRD and implementation issues

            cartographer/
                The Cartographer PRD and implementation issues

            barracks/
                The Barracks PRD and implementation issues

            any other documentation you want

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

        barracks/
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
    issues/
        contains docs for all current issues generated
    raplh/
        script to run a raplh loop that runs the issues
```
