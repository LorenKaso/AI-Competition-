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
        self._id = "Loren-K"
        self.current_target_id = None
        self.critical_target_id = None
        self.optimal_range = 100
        self.evading_ticks = 0
        self.last_attacker_id = None

    @property
    def id(self) -> str:
        return self._id
    
    
    def get_least_crowded_zone(self, my_ship, enemy_ships):
        zone_counts = [0, 0, 0, 0]  # אזור 0 = שמאל עליון, 1 = ימין עליון, 2 = שמאל תחתון, 3 = ימין תחתון
        mid_x, mid_y = 1000, 1000  # שימי את אמצע המפה לפי הגודל האמיתי

        for enemy in enemy_ships:
            if enemy['x'] < mid_x and enemy['y'] < mid_y:
                zone_counts[0] += 1
            elif enemy['x'] >= mid_x and enemy['y'] < mid_y:
                zone_counts[1] += 1
            elif enemy['x'] < mid_x and enemy['y'] >= mid_y:
                zone_counts[2] += 1
            else:
                zone_counts[3] += 1

        # מציאת האזור עם הכי מעט אויבים
        least_crowded = zone_counts.index(min(zone_counts))

        # חשבי נקודת יעד באזור הזה (מרכזו)
        if least_crowded == 0:
            target_x, target_y = mid_x * 0.5, mid_y * 0.5
        elif least_crowded == 1:
            target_x, target_y = mid_x * 1.5, mid_y * 0.5
        elif least_crowded == 2:
            target_x, target_y = mid_x * 0.5, mid_y * 1.5
        else:
            target_x, target_y = mid_x * 1.5, mid_y * 1.5

        return target_x, target_y


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

        # 🧭 נוע מראש לאזור עם הכי מעט אויבים, אם לא תחת איום ולא באמצע קרב עם יריב פצוע
        if self.evading_ticks == 0 and not self.critical_target_id:
            target_x, target_y = self.get_least_crowded_zone(my_ship, enemy_ships)
            dx = target_x - my_ship['x']
            dy = target_y - my_ship['y']
            angle_to_zone = math.degrees(math.atan2(dy, dx))
            angle_diff_zone = (angle_to_zone - my_ship['angle'] + 360) % 360
            if angle_diff_zone > 180:
                angle_diff_zone -= 360

            distance_to_zone = math.hypot(dx, dy)

            if distance_to_zone > 100:
                if abs(angle_diff_zone) < 15:
                    return Action.ACCELERATE
                else:
                    return Action.ROTATE_RIGHT if angle_diff_zone > 0 else Action.ROTATE_LEFT

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

            

    # אם יש תוקף שאינו המטרה – תגיב קודם עם תנועה סיבובית התקפית
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

                distance_to_threat = math.hypot(dx, dy)

                # ירי תוך כדי תנועה סיבובית
                if abs(angle_diff) < 25:
                    # קרוב מדי? תזוז תוך כדי ירי
                    if distance_to_threat < 200:
                        return random.choice([
                            Action.SHOOT,
                            Action.ROTATE_LEFT,
                            Action.ROTATE_RIGHT,
                            Action.ACCELERATE
                        ])
                    else:
                        return Action.SHOOT
                else:
                    # נסי להתכוונן אליו תוך תנועה
                    return Action.ROTATE_RIGHT if angle_diff > 0 else Action.ROTATE_LEFT

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

        # 🔫 אם יש ספינה ממש צמודה – ירי בלתי פוסק
        for enemy in enemy_ships:
            dx = enemy['x'] - my_ship['x']
            dy = enemy['y'] - my_ship['y']
            distance_to_enemy = math.hypot(dx, dy)

            if distance_to_enemy < 5:  # "מרחק אפס"
                return Action.SHOOT

        # ⚔️ אם הזמן קרוב לסיום – תקוף את הספינה עם הכי הרבה נקודות
        if game_state.ticks_remaining < 1500:
            strongest_enemy = max(enemy_ships, key=lambda s: s['score'])
            dx = strongest_enemy['x'] - my_ship['x']
            dy = strongest_enemy['y'] - my_ship['y']
            angle_to_strong = math.degrees(math.atan2(dy, dx))
            angle_diff_strong = (angle_to_strong - my_ship['angle'] + 360) % 360
            if angle_diff_strong > 180:
                angle_diff_strong -= 360

            distance_to_strong = math.hypot(dx, dy)

            if abs(angle_diff_strong) < 10:
                if distance_to_strong > self.optimal_range:
                    return Action.ACCELERATE
                else:
                    return Action.SHOOT
            else:
                return Action.ROTATE_RIGHT if angle_diff_strong > 0 else Action.ROTATE_LEFT

        # שלב תקיפה מוגברת - כשנשארו פחות מ-2000 טיקים
        if game_state.ticks_remaining < 2000:
            # תקוף את הספינה עם הכי הרבה נקודות
            aggressive_target = max(enemy_ships, key=lambda s: s['score'])
            dx = aggressive_target['x'] - my_ship['x']
            dy = aggressive_target['y'] - my_ship['y']
            angle_to_agg = math.degrees(math.atan2(dy, dx))
            angle_diff_agg = (angle_to_agg - my_ship['angle'] + 360) % 360
            if angle_diff_agg > 180:
                angle_diff_agg -= 360

            distance_to_agg = math.hypot(dx, dy)

            if abs(angle_diff_agg) < 25:
                if distance_to_agg > self.optimal_range * 0.8:
                    return Action.ACCELERATE
                else:
                    return Action.SHOOT
            else:
                return Action.ROTATE_RIGHT if angle_diff_agg > 0 else Action.ROTATE_LEFT

        # חישוב ירי חכם עם תנועה זורמת
        should_shoot = abs(angle_diff) < 20 and distance < 500

        if abs(angle_diff) < 15:
            if distance < self.optimal_range * 0.6:
                return Action.BRAKE  # קרובה מדי - התרחקי
            elif distance > self.optimal_range:
                return Action.ACCELERATE  # רחוקה מדי - תתקרבי
            else:
                return Action.SHOOT  # מרחק טוב ומכוונת - תירה
        else:
            return Action.ROTATE_RIGHT if angle_diff > 0 else Action.ROTATE_LEFT

    