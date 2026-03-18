"""
main.py – Flappy Fish entry point.

Run from the project root:
    python src/main.py
Or from inside src/:
    python main.py
"""

from game import Game


def main() -> None:
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
