from brain_interface import SpaceshipBrain, Action, GameState
import math
import random

class RandomBrain(SpaceshipBrain):
    def __init__(self):
        self.current_action = None
        self.action_counter = 0
        self.action_duration = 5  # Number of frames to keep the same action
        self.safe_margin = 100  # מרחק בטוח מהקצה

    @property
    def id(self) -> str:
        return "Random"

    def decide_what_to_do_next(self, game_state: GameState) -> Action:
        # Choose new random action after action_duration frames

        my_ship = next((s for s in game_state.ships if s['id'] == self.id), None)
        if not my_ship:
            return Action.ROTATE_RIGHT  # ברירת מחדל אם הספינה לא נמצאה

        # קצוות המפה
        x = my_ship['x']
        y = my_ship['y']
        width = game_state.map_width
        height = game_state.map_height

        near_left = x < self.safe_margin
        near_right = x > width - self.safe_margin
        near_top = y < self.safe_margin
        near_bottom = y > height - self.safe_margin

        # אם קרובים לקצה → שינוי כיוון
        if near_left or near_right or near_top or near_bottom:
            self.action_counter = 0
            return random.choice([Action.ROTATE_LEFT, Action.ROTATE_RIGHT, Action.BRAKE])

        # אחרת – בחר פעולה אקראית כל action_duration פריימים
        if self.current_action is None or self.action_counter >= self.action_duration:
            self.current_action = random.choice([Action.ACCELERATE, Action.ROTATE_LEFT, Action.ROTATE_RIGHT])
            self.action_counter = 0

        self.action_counter += 1
        return self.current_action

     