import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AtlasGameFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_pixel_adventure_uses_grid_collision_and_progressive_interaction(self):
        """A pixel route without grid collision or gated interaction is just an animated page."""
        script = """
const pixel = require(process.argv[1]);
let state = pixel.createPixelGame();
const start = state.player;
const moved = pixel.move(state, 1, 0);
const blocked = pixel.move({...moved, player: {x: 7, y: 5}}, 1, 0);
const shard = pixel.interact({...state, player: {x: 4, y: 7}}, {shards: []});
const repeat = pixel.interact({...state, player: {x: 4, y: 7}}, {shards: ["state"]});
const npcLocked = pixel.interact({...state, player: {x: 12, y: 7}}, {shards: ["state"]});
const npcReady = pixel.interact({...state, player: {x: 12, y: 7}}, {shards: ["state", "repeat", "control"]});
process.stdout.write(JSON.stringify({start, moved, blocked, shard, repeat, npcLocked, npcReady}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "pixel_adventure_engine.js"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertGreater(result["moved"]["player"]["x"], result["start"]["x"])
        self.assertEqual(result["blocked"]["player"]["x"], 7)
        self.assertEqual(result["shard"]["event"], "shard")
        self.assertEqual(result["shard"]["id"], "state")
        self.assertEqual(result["repeat"]["event"], "none")
        self.assertEqual(result["npcLocked"]["event"], "locked")
        self.assertEqual(result["npcReady"]["event"], "npc")

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_pixel_scenes_and_river_collision_keep_the_bridge_open(self):
        """The river must block travel except at the bridge, and regions need names."""
        script = """
const pixel = require(process.argv[1]);
const scenes = [
  pixel.sceneAt({x: 3, y: 13}),
  pixel.sceneAt({x: 11, y: 7}),
  pixel.sceneAt({x: 19, y: 12})
];
const waterBlocked = pixel.move({player: {x: 9, y: 6}}, 1, 0);
const bridgeOpen = pixel.move({player: {x: 9, y: 7}}, 1, 0);
process.stdout.write(JSON.stringify({scenes, waterBlocked, bridgeOpen}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "pixel_adventure_engine.js"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["scenes"], ["village", "river", "archive"])
        self.assertEqual(result["waterBlocked"]["player"]["x"], 9)
        self.assertEqual(result["bridgeOpen"]["player"]["x"], 10)

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_pixel_guide_has_three_actions_and_quantum_phase_metadata(self):
        script = """
const pixel = require(process.argv[1]);
process.stdout.write(JSON.stringify({steps: pixel.GUIDE_STEPS, scenes: pixel.SCENES, moveInterval: pixel.MOVE_INTERVAL}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "pixel_adventure_engine.js"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual([step["id"] for step in result["steps"]], ["move", "observe", "bridge"])
        self.assertTrue(all(step["action"] for step in result["steps"]))
        self.assertEqual(result["scenes"]["river"]["phase"], "entangled")
        self.assertGreaterEqual(result["moveInterval"], 0.1)

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_pixel_story_and_obstacle_layers_are_separate_from_background(self):
        """Story beats and collision objects must remain data, not baked into the background bitmap."""
        script = """
const pixel = require(process.argv[1]);
process.stdout.write(JSON.stringify({
  story: pixel.STORY_BEATS.map((beat) => beat.id),
  buildingIds: pixel.BUILDINGS.map((building) => building.id),
  obstacle: pixel.obstacleAt(5, 3),
  open: pixel.obstacleAt(6, 3)
}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "pixel_adventure_engine.js"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["story"], ["arrival", "fragments", "crossing", "well", "choice"])
        self.assertIn("outpost", result["buildingIds"])
        self.assertIsNotNone(result["obstacle"])
        self.assertIsNone(result["open"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_adventure_world_moves_collides_and_unlocks_interactions(self):
        """A missing collision or quest gate would let players walk through the case."""
        script = """
const world = require(process.argv[1]);
let state = world.createWorld();
const start = state.player;
state = world.move(state, 1, 0, 0.5, {clues: []});
const moved = state.player;

const blockedState = {...state, player: {x: 607, y: 525, facing: "right"}};
const blocked = world.move(blockedState, 1, 0, 0.5, {clues: []});
const unlocked = world.move(
  blockedState,
  1,
  0,
  0.5,
  {clues: ["state", "possibility", "repeat", "control"]}
);

const clueState = {...state, player: {x: 370, y: 690, facing: "up"}};
const clue = world.interact(clueState, {clues: []});
const collectedClue = world.interact(clueState, {clues: ["state"]});

const consoleState = {...state, player: {x: 965, y: 520, facing: "up"}};
const consoleLocked = world.interact(consoleState, {clues: []});
const consoleReady = world.interact(consoleState, {
  clues: ["state", "possibility", "repeat", "control"]
});

process.stdout.write(JSON.stringify({start, moved, blocked, unlocked, clue, collectedClue, consoleLocked, consoleReady}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "atlas_adventure_engine.js"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertGreater(result["moved"]["x"], result["start"]["x"])
        self.assertEqual(result["blocked"]["player"]["x"], 607)
        self.assertGreater(result["unlocked"]["player"]["x"], 607)
        self.assertEqual(result["clue"]["event"], "clue")
        self.assertEqual(result["clue"]["id"], "state")
        self.assertEqual(result["collectedClue"]["event"], "none")
        self.assertEqual(result["consoleLocked"]["event"], "locked")
        self.assertEqual(result["consoleReady"]["event"], "experiment")

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_investigation_actions_unlock_the_world_and_build_a_score(self):
        passport = {
            "schema_version": "loomq-inquiry-passport-v1",
            "conclusion_audits": {
                "h-opens-branches-cx-correlates": {
                    "status": "supported",
                    "claim": "H creates branches and CX changes correlation.",
                    "reason": "The controlled experiment changes at g2.",
                }
            },
        }
        script = """
const game = require(process.argv[1]);
let state = game.createGame();
const initial = game.locationProgress(state);
for (const clue of ["state", "possibility", "repeat", "control"]) {
  state = game.collectClue(state, clue);
}
const briefed = game.locationProgress(state);
state = game.recordPrediction(state, "h-opens-branches");
state = game.attachPassport(state, JSON.parse(process.argv[2]));
const experimented = game.locationProgress(state);
state = game.auditConclusion(state, "h-opens-branches-cx-correlates");
process.stdout.write(JSON.stringify({
  initial,
  briefed,
  experimented,
  final: game.locationProgress(state),
  state,
}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "atlas_game_engine.js"),
                json.dumps(passport),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(
            [item["state"] for item in result["initial"]],
            ["current", "locked", "locked"],
        )
        self.assertEqual(
            [item["state"] for item in result["briefed"]],
            ["complete", "current", "locked"],
        )
        self.assertEqual(
            [item["state"] for item in result["experimented"]],
            ["complete", "complete", "current"],
        )
        self.assertEqual(
            [item["state"] for item in result["final"]],
            ["complete", "complete", "complete"],
        )
        self.assertEqual(result["state"]["score"], 100)
        self.assertEqual(result["state"]["audit"]["status"], "supported")

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_locked_travel_and_unknown_clues_fail_closed(self):
        script = """
const game = require(process.argv[1]);
const state = game.createGame();
const errors = [];
for (const action of [
  () => game.travel(state, "field"),
  () => game.collectClue(state, "invented"),
  () => game.attachPassport(state, {}),
]) {
  try { action(); } catch (error) { errors.push(error.message); }
}
process.stdout.write(JSON.stringify(errors));
"""
        completed = subprocess.run(
            [shutil.which("node"), "-e", script, str(ROOT / "web" / "atlas_game_engine.js")],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        errors = json.loads(completed.stdout)
        self.assertEqual(len(errors), 3)
        self.assertIn("尚未解锁", errors[0])
        self.assertIn("未知调查线索", errors[1])
        self.assertIn("实验护照", errors[2])

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_rerunning_the_experiment_requires_a_fresh_audit(self):
        passport = {
            "schema_version": "loomq-inquiry-passport-v1",
            "conclusion_audits": {
                "supported": {
                    "status": "supported",
                    "claim": "claim",
                    "reason": "reason",
                }
            },
        }
        script = """
const game = require(process.argv[1]);
const passport = JSON.parse(process.argv[2]);
let state = game.createGame();
for (const clue of game.CLUES) state = game.collectClue(state, clue);
state = game.recordPrediction(state, "prediction");
state = game.attachPassport(state, passport);
state = game.auditConclusion(state, "supported");
state = game.attachPassport(state, passport);
process.stdout.write(JSON.stringify({state, progress: game.locationProgress(state)}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "atlas_game_engine.js"),
                json.dumps(passport),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertIsNone(result["state"]["audit"])
        self.assertEqual(result["state"]["score"], 50)
        self.assertEqual(
            [item["state"] for item in result["progress"]],
            ["complete", "complete", "current"],
        )
