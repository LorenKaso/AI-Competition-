from brain_interface import SpaceshipBrain, Action, GameState
import math
import random

CHANCE_TO_USE_NITRO = 0.01 # 1% chance per decision tick
CHANCE_TO_PLACE_MINE = 0.02 # 2% chance per decision tick
CHANCE_TO_USE_SHIELD = 0.015 # 1.5% chance per decision tick

# קבועים נוספים שיעזרו לנו (ניתן להתאים אותם לפי ניסוי וטעייה)
LOW_HEALTH_THRESHOLD = 30 # בריאות נמוכה
CRITICAL_HEALTH_THRESHOLD = 15 # בריאות קריטית
SHIELD_ACTIVATION_RANGE = 150 # טווח קצר לאויב שמצדיק הפעלת מגן
MINE_PLACEMENT_DISTANCE = 50 # טווח קרוב להניח מוקש
EVASION_DURATION = 15 # משך זמן התחמקות
AIM_THRESHOLD = 5 # מעלות - כמה קרוב צריך להיות מכוון כדי לירות

class AggressiveHunterBrain(SpaceshipBrain):
    def __init__(self):
        self._id = "CPU4"
        self.current_target_id = None
        self.optimal_range = 100

    @property
    def id(self) -> str:
        return self._id

    def decide_what_to_do_next(self, game_state: GameState) -> Action:
        #print("Deciding what to do next...")
        # Find my ship
        try:
            my_ship = next(ship for ship in game_state.ships if ship['id'] == self.id)
        except StopIteration:
            return Action.ROTATE_RIGHT  # Default action if my ship isn't found

        # Find all enemy ships that aren't destroyed (health > 0)
        enemy_ships = [ship for ship in game_state.ships 
                      if ship['id'] != self.id and ship['health'] > 0]

        if not enemy_ships:
            self.current_target_id = None  # Reset target if no enemies are left
            return Action.ROTATE_RIGHT

        # Select target - either keep current or pick closest if no valid target
        current_target = next((ship for ship in enemy_ships if ship['id'] == self.current_target_id), None)
        if not current_target or current_target['health'] <= 0:
            current_target = min(enemy_ships, 
                key=lambda ship: math.hypot(ship['x'] - my_ship['x'], ship['y'] - my_ship['y']))
            self.current_target_id = current_target['id']


        # Calculate angle to target
        dx = current_target['x'] - my_ship['x']
        dy = current_target['y'] - my_ship['y']
        target_line_angle = math.degrees(math.atan2(dy, dx))

        # Calculate angle difference and normalize to -180 to 180
        angle_diff = (target_line_angle - my_ship['angle'] + 360) % 360
        if angle_diff > 180:
            angle_diff -= 360  # Normalize to -180 to 180 range

        # Get distance to target
        distance = math.hypot(dx, dy)

        # Nitro Logic
        if random.random() < CHANCE_TO_USE_NITRO:
            return Action.NITRO

        # Shield Activation Logic
        if 'shields_available' in my_ship and my_ship['shields_available'] > 0 and \
           'is_shield_active' in my_ship and not my_ship['is_shield_active'] and \
           random.random() < CHANCE_TO_USE_SHIELD:
            return Action.ACTIVATE_SHIELD

        # Mine Placing Logic
        if 'mines_available' in my_ship and my_ship['mines_available'] > 0 and \
           random.random() < CHANCE_TO_PLACE_MINE:
            return Action.PLACE_MINE

        # Check if target is ahead within shooting range
        if abs(angle_diff) < 15:  # Angle difference is small enough to be considered "ahead"
            if distance < self.optimal_range:
                #print("Within optimal range. Shooting.")
                return Action.SHOOT
            elif distance > self.optimal_range:
                #print("Beyond optimal range. Accelerating towards target.")
                return Action.ACCELERATE
            else:
                #print("Within acceptable range. Braking.")
                return Action.BRAKE

        # Turn toward target
        if angle_diff > 0:
            #print("Rotating right towards target.")
            return Action.ROTATE_RIGHT
        #print("Rotating left towards target.")
        return Action.ROTATE_LEFT
