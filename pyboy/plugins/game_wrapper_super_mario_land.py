#
# License: See LICENSE.md file
# GitHub: https://github.com/Baekalfen/PyBoy
#
__pdoc__ = {
    "GameWrapperSuperMarioLand.cartridge_title": False,
    "GameWrapperSuperMarioLand.post_tick": False,
}

import logging

from pyboy.utils import WindowEvent

from .base_plugin import PyBoyGameWrapper

logger = logging.getLogger(__name__)

try:
    from cython import compiled
    cythonmode = compiled
except ImportError:
    cythonmode = False


class GameWrapperSuperMarioLand(PyBoyGameWrapper):
    """
    This class wraps Super Mario Land, and provides easy access to score, coins, lives left, time left, world and a
    "fitness" score for AIs.

    If you call `print` on an instance of this object, it will show an overview of everything this object provides.
    """
    cartridge_title = "SUPER MARIOLAN"

    def __init__(self, *args, **kwargs):
        self.shape = (20, 16)
        """The shape of the game area"""
        self.world = (0, 0)
        """Provides the current "world" Mario is in, as a tuple of as two integers (world, level)."""
        self.coins = 0
        """The number of collected coins."""
        self.lives_left = 0
        """The number of lives Mario has left"""
        self.score = 0
        """The score provided by the game"""
        self.time_left = 0
        """The number of seconds left to finish the level"""
        self.level_progress = 0
        """An integer of the current "global" X position in this level. Can be used for AI scoring."""
        self._level_progress_max = 0
        self.fitness = 0
        """
        A built-in fitness scoring. Taking points, level progression, time left, and lives left into account.

        .. math::
            fitness = (lives\\_left \\cdot 10000) + (score + time\\_left \\cdot 10) + (\\_level\\_progress\\_max \\cdot 10)
        """

        super().__init__(*args, game_area_section=(0, 2) + self.shape, game_area_wrap_around=True, **kwargs)

    def post_tick(self):
        self._tile_cache_invalid = True
        self._sprite_cache_invalid = True

        self.world = self.tilemap_background[12, 1] - 256, self.tilemap_background[14, 1] - 256
        blank = 300
        self.coins = self._sum_number_on_screen(9, 1, 2, blank, -256)
        self.lives_left = self._sum_number_on_screen(6, 0, 2, blank, -256)
        self.score = self._sum_number_on_screen(0, 1, 6, blank, -256)
        self.time_left = self._sum_number_on_screen(17, 1, 3, blank, -256)

        level_block = self.pyboy.get_memory_value(0xC0AB)
        mario_x = self.pyboy.get_memory_value(0xC202)
        scx = self.pyboy.botsupport_manager().screen().tilemap_position_list()[16][0]
        self.level_progress = level_block*16 + (scx-7) % 16 + mario_x

        if self.game_has_started:
            self._level_progress_max = max(self.level_progress, self._level_progress_max)
            end_score = self.score + self.time_left * 10
            self.fitness = self.lives_left * 10000 + end_score + self._level_progress_max * 10

    def start_game(self):
        """
        Call this function right after initializing PyBoy. This will start a game in world 1-1 and give back control on
        the first frame it's possible.

        The state of the emulator is saved, and using `reset_game`, you can get back to this point of the game
        instantly.
        """
        if not self.pyboy.frame_count == 0:
            logger.warning("Calling start_game from an already running game. This might not work.")

        # Boot screen
        while True:
            self.pyboy.tick()
            if self.tilemap_background[6:11, 13] == [284, 285, 266, 283, 285]: # "START" on the main menu
                break
        self.pyboy.tick()
        self.pyboy.tick()
        self.pyboy.tick()

        self.pyboy.send_input(WindowEvent.PRESS_BUTTON_START)
        self.pyboy.tick()
        self.pyboy.send_input(WindowEvent.RELEASE_BUTTON_START)

        while True:
            self.pyboy.tick()
            self.tilemap_background.refresh_lcdc()

            # "MARIO" in the title bar and 0 is placed at score
            if self.tilemap_background[0:5, 0] == [278, 266, 283, 274, 280] and \
               self.tilemap_background[5, 1] == 256:
                self.game_has_started = True
                break

        self.saved_state.seek(0)
        self.pyboy.save_state(self.saved_state)

    def reset_game(self):
        """
        After calling `start_game`, use this method to reset Mario to the beginning of world 1-1.

        If you want to reset to later parts of the game -- for example world 1-2 or 3-1 -- use the methods
        `pyboy.PyBoy.save_state` and `pyboy.PyBoy.load_state`.
        """
        if self.game_has_started:
            self.saved_state.seek(0)
            self.pyboy.load_state(self.saved_state)
            self.post_tick()
        else:
            logger.error("Tried to reset game, but it hasn't been started yet!")

    def game_area(self):
        """
        Use this method to get a matrix of the "game area" of the screen. This view is simplified to be perfect for
        machine learning applications.

        In Super Mario Land, this is almost the entire screen, expect for the top part showing the score, lives left
        and so on. These values can be found in the variables of this class.

        In this example, Mario is `0`, `1`, `16` and `17`. He is standing on the ground which is `352` and `353`:
        ```text
             0   1   2   3   4   5   6   7   8   9   10  11  12  13  14  15  16  17  18  19
        ____________________________________________________________________________________
        0  | 339 339 339 339 339 339 339 339 339 339 339 339 339 339 339 339 339 339 339 339
        1  | 320 320 320 320 320 320 320 320 320 320 320 320 320 320 320 320 320 320 320 320
        2  | 300 300 300 300 300 300 300 300 300 300 300 300 321 322 321 322 323 300 300 300
        3  | 300 300 300 300 300 300 300 300 300 300 300 324 325 326 325 326 327 300 300 300
        4  | 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300
        5  | 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300
        6  | 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300 300
        7  | 300 300 300 300 300 300 300 300 310 350 300 300 300 300 300 300 300 300 300 300
        8  | 300 300 300 300 300 300 300 310 300 300 350 300 300 300 300 300 300 300 300 300
        9  | 300 300 300 300 300 129 310 300 300 300 300 350 300 300 300 300 300 300 300 300
        10 | 300 300 300 300 300 310 300 300 300 300 300 300 350 300 300 300 300 300 300 300
        11 | 300 300 310 350 310 300 300 300 300 306 307 300 300 350 300 300 300 300 300 300
        12 | 300 368 369 300 0   1   300 306 307 305 300 300 300 300 350 300 300 300 300 300
        13 | 310 370 371 300 16  17  300 305 300 305 300 300 300 300 300 350 300 300 300 300
        14 | 352 352 352 352 352 352 352 352 352 352 352 352 352 352 352 352 352 352 352 352
        15 | 353 353 353 353 353 353 353 353 353 353 353 353 353 353 353 353 353 353 353 353
        ```

        Returns
        -------
        memoryview:
            Simplified 2-dimensional memoryview of the screen
        """
        return PyBoyGameWrapper.game_area(self)

    def __repr__(self):
        adjust = 4
        # yapf: disable
        return (
            f"Super Mario Land: World {'-'.join([str(i) for i in self.world])}\n" +
            f"Coins: {self.coins}\n" +
            f"lives_left: {self.lives_left}\n" +
            f"Score: {self.score}\n" +
            f"Time left: {self.time_left}\n" +
            f"Level progress: {self.level_progress}\n" +
            f"Fitness: {self.fitness}\n" +
            "Sprites on screen:\n" +
            "\n".join([str(s) for s in self._sprites_on_screen()]) +
            "\n" +
            "Tiles on screen:\n" +
            " "*5 + "".join([f"{i: <4}" for i in range(20)]) + "\n" +
            "_"*(adjust*20+4) +
            "\n" +
            "\n".join(
                [
                    f"{i: <3}| " + "".join([str(tile).ljust(adjust) for tile in line])
                    for i, line in enumerate(self.game_area())
                ]
            )
        )
        # yapf: enable
