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

class LorenKSpaceshipBrain(SpaceshipBrain):
    def __init__(self):
        self._id = "Loren-k"
        self.current_target_id = None
        self.critical_target_id = None
        self.optimal_range = 100
        self.evading_ticks = 0
        self.last_attacker_id = None

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
        
        # איתור אויבים פצועים (בריאות פחות מ-50)
        wounded_enemies = [ship for ship in enemy_ships if ship['health'] < 50]
        if wounded_enemies:
            wounded_target = min(wounded_enemies, key=lambda s: math.hypot(s['x'] - my_ship['x'], s['y'] - my_ship['y']))
            self.critical_target_id = wounded_target['id']
        else:
            self.critical_target_id = None

        # קודם כל ננסה למצוא אויבים עם פחות מ-50% חיים
        weak_enemies = [ship for ship in enemy_ships if ship['health'] < 50]

        if weak_enemies:
            # נבחר את הקרוב מביניהם
            current_target = min(weak_enemies, 
                key=lambda ship: math.hypot(ship['x'] - my_ship['x'], ship['y'] - my_ship['y']))
        else:
            # אם אין אויבים חלשים – נחפש את הקרוב מבין כולם
            current_target = min(enemy_ships, 
                key=lambda ship: math.hypot(ship['x'] - my_ship['x'], ship['y'] - my_ship['y']))

        self.current_target_id = current_target['id']

        # בודקים אם מישהו אחר יורה עליי (לא המטרה הנוכחית)
        incoming_threats = []
        for bullet in game_state.bullets:
            shooter_id = bullet.get('owner_id')
            if shooter_id and shooter_id != self.id and shooter_id != self.current_target_id:
                dx_bullet = my_ship['x'] - bullet['x']
                dy_bullet = my_ship['y'] - bullet['y']
                distance = math.hypot(dx_bullet, dy_bullet)

                # נחשב אם הכדור מתקרב
                if distance < 150:  # טווח איום
                    incoming_threats.append((shooter_id, distance))

            

    # אם יש תוקף שאינו המטרה – תגיב קודם
        if incoming_threats:
            threat_id, _ = min(incoming_threats, key=lambda t: t[1])
            threat_ship = next((s for s in enemy_ships if s['id'] == threat_id), None)

            if threat_ship:
                self.evading_ticks = EVASION_DURATION
                self.last_attacker_id = threat_id
                
                dx = threat_ship['x'] - my_ship['x']
                dy = threat_ship['y'] - my_ship['y']
                angle_to_threat = math.degrees(math.atan2(dy, dx))
                angle_diff = (angle_to_threat - my_ship['angle'] + 360) % 360
                if angle_diff > 180:
                    angle_diff -= 360

                if abs(angle_diff) < 38:
                    return Action.SHOOT
                else:
                    return random.choice([Action.ROTATE_LEFT, Action.ROTATE_RIGHT])

    # שלב 5: רדיפה אחרי יריב חלש כל עוד הוא קיים
        if self.critical_target_id:
            weak_target = next((s for s in enemy_ships if s['id'] == self.critical_target_id), None)
            if weak_target:
                dx = weak_target['x'] - my_ship['x']
                dy = weak_target['y'] - my_ship['y']
                angle_to_weak = math.degrees(math.atan2(dy, dx))
                angle_diff_weak = (angle_to_weak - my_ship['angle'] + 360) % 360
                if angle_diff_weak > 180:
                    angle_diff_weak -= 360

                distance_to_weak = math.hypot(dx, dy)

                # אם מכוון טוב ליריב החלש – תירה, או תתקרב אם רחוק מדי
                if abs(angle_diff_weak) < 38:
                    if distance_to_weak > self.optimal_range:
                        return Action.ACCELERATE
                    return Action.SHOOT
                else:
                    return Action.ROTATE_RIGHT if angle_diff_weak > 0 else Action.ROTATE_LEFT

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

        # חישוב ירי חכם עם תנועה זורמת
        should_shoot = abs(angle_diff) < 20 and distance < 500

        if abs(angle_diff) < 10:
            if distance > self.optimal_range:
                action = Action.ACCELERATE
            else:
                action = Action.BRAKE
        else:
            action = Action.ROTATE_RIGHT if angle_diff > 0 else Action.ROTATE_LEFT

        # החזר ירי אם אפשר, אחרת תנועה
        if should_shoot:
            return Action.SHOOT

        return action

        # Turn toward target
        if angle_diff > 0:
            #print("Rotating right towards target.")
            return Action.ROTATE_RIGHT
        #print("Rotating left towards target.")
        return Action.ROTATE_LEFT
