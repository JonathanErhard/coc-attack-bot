"""
Auto Attacker - Automated continuous attack system for COC
"""

import time
import random
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pyautogui
import keyboard

from .attack_player import AttackPlayer
from .screen_capture import ScreenCapture
from .coordinate_mapper import CoordinateMapper
from .ai_analyzer import AIAnalyzer
from ..utils.logger import Logger
from ..utils.config import Config

from PIL import ImageGrab
import numpy as np
import cv2 as cv

class AutoAttacker:
    """Automated continuous attack system"""
    
    def __init__(self, attack_player: AttackPlayer, screen_capture: ScreenCapture, 
                 coordinate_mapper: CoordinateMapper, logger: Logger, ai_analyzer: AIAnalyzer, config: Config):
        self.attack_player = attack_player
        self.screen_capture = screen_capture
        self.coordinate_mapper = coordinate_mapper
        self.logger = logger
        self.ai_analyzer = ai_analyzer
        self.config = config
        
        self.is_running = False
        self.auto_thread = None
        self.stats = {
            'total_attacks': 0,
            'successful_attacks': 0,
            'failed_attacks': 0,
            'start_time': None,
            'last_attack_time': None
        }
        
        self.attack_sessions = self.config.get('auto_attacker.attack_sessions', [])
        self.max_search_attempts = self.config.get('auto_attacker.max_search_attempts', 10)
        self.current_session_index = 0
        
        print("Auto Attacker initialized")
        print("Emergency stop: Ctrl+Alt+S")
    
    def add_attack_session(self, session_name: str) -> bool:
        """Add an attack session to rotation"""
        sessions = self.config.get('auto_attacker.attack_sessions', [])
        if session_name not in sessions:
            sessions.append(session_name)
            self.config.set('auto_attacker.attack_sessions', sessions)
            self.attack_sessions = sessions
            self.logger.info(f"Added attack session: {session_name}")
            return True
        return False
    
    def remove_attack_session(self, session_name: str) -> bool:
        """Remove an attack session from rotation"""
        sessions = self.config.get('auto_attacker.attack_sessions', [])
        if session_name in sessions:
            sessions.remove(session_name)
            self.config.set('auto_attacker.attack_sessions', sessions)
            self.attack_sessions = sessions
            self.logger.info(f"Removed attack session: {session_name}")
            return True
        return False
    
    def start_auto_attack(self) -> None:
        """Start the automated attack system"""
        if self.is_running:
            print("Auto attacker already running")
            return
        
        if not self.attack_sessions:
            self.logger.error("No attack sessions configured. Please add at least one session.")
            return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        self.auto_thread = threading.Thread(target=self._auto_attack_loop)
        self.auto_thread.daemon = True
        self.auto_thread.start()
        
        self.logger.info("Auto attacker started")
    
    def stop_auto_attack(self) -> None:
        """Stop the automated attack system"""
        if not self.is_running:
            return
        
        self.logger.info("Auto attacker stopping...")
        self.is_running = False
        
        # Stop any playing attack
        self.attack_player.stop_playback()
        
        if self.auto_thread and self.auto_thread.is_alive():
            self.auto_thread.join(timeout=5)
        
        self.logger.info("Auto attacker stopped")
    
    def _auto_attack_loop(self) -> None:
        """Main automation loop"""
        try:
            while self.is_running:
                # Check emergency stop
                if keyboard.is_pressed('ctrl+alt+s'):
                    self.logger.warning("Emergency stop activated!")
                    break
                
                self.logger.info("🎯 Starting new attack cycle...")
                
                # Execute attack sequence
                if self._execute_attack_sequence():
                    self.stats['successful_attacks'] += 1
                    self.logger.info("✅ Attack sequence completed successfully")
                else:
                    self.stats['failed_attacks'] += 1
                    self.logger.warning("❌ Attack sequence failed")
                
                self.stats['total_attacks'] += 1
                self.stats['last_attack_time'] = datetime.now()
                
                # Short break between attacks
                if self.is_running:
                    delay = random.randint(5, 15)
                    self.logger.info(f"⏳ Waiting {delay} seconds before next attack...")
                    time.sleep(delay)
                    
        except Exception as e:
            self.logger.error(f"Auto attack loop error: {e}")
        finally:
            self.is_running = False
    
    def collect_loot(self):
        coords = self.coordinate_mapper.get_coordinates()

        #scroll to reveal cart
        pyautogui.moveTo(1288, 1301)
        pyautogui.scroll(-100)
        time.sleep(0.21)
        pyautogui.scroll(-100)
        time.sleep(0.29)
        pyautogui.scroll(-100)
        time.sleep(0.21)

        pyautogui.moveTo(1571, 205)
        pyautogui.dragTo(1167, 1235, duration=0.5)
        time.sleep(0.22)

        if 'loot_cart' not in coords:
                self.logger.warning("Loot cart button not mapped, skipping loot collection")
        else:
            loot_cart_coord = self._get_cart_position()
            self.logger.info(f"🔍 Checking for loot cart at ({loot_cart_coord[0]}, {loot_cart_coord[1]})")
            pyautogui.click(loot_cart_coord[0], loot_cart_coord[1])
            time.sleep(3)  # Wait for loot collection to complete
        if 'collect_loot' in coords:
            collect_coord = coords['collect_loot']
            self.logger.info(f"Collecting loot at ({collect_coord['x']}, {collect_coord['y']})")
            pyautogui.click(collect_coord['x'], collect_coord['y'])
            time.sleep(3)  # Wait for loot collection to complete
        if 'close_loot' in coords:
            close_coord = coords['close_loot']
            self.logger.info(f"Closing loot screen at ({close_coord['x']}, {close_coord['y']})")
            pyautogui.click(close_coord['x'], close_coord['y'])
            time.sleep(2)  # Wait for screen to close

    def _check_phase1_ended(self, threshold: float = 128) -> bool:
        coords = self.coordinate_mapper.get_coordinates()
        tl = coords['top_left_od']
        br = coords['bottom_right_od']
        x1, y1 = tl['x'], tl['y']
        x2, y2 = br['x'], br['y']
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        pixels = np.array(screenshot)

        brightness = (
            0.33 * pixels[:, :, 0] +
            0.33 * pixels[:, :, 1] +
            0.33 * pixels[:, :, 2]
        )

        print(f"Phase 1 brightness sum: {int(np.sum(brightness >= threshold))}")
        return int(np.sum(brightness >= threshold)) < 2000

    def _check_attack_finished(self, threshold=128) -> bool:
        coords = self.coordinate_mapper.get_coordinates()
        tl = coords['top_left_ret']
        br = coords['bottom_right_ret']
        x1, y1 = tl['x'], tl['y']
        x2, y2 = br['x'], br['y']
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        pixels = np.array(screenshot)

        brightness = (
            0.33 * pixels[:, :, 0] +
            0.33 * pixels[:, :, 1] +
            0.33 * pixels[:, :, 2]
        )
        bright_pixels = int(np.sum(brightness >= threshold))
        print(f"Attack button white pixels: {bright_pixels}")
        
        p = np.array(ImageGrab.grab(bbox=(x1, y1, x2, y2))).astype(float)

        r, g, b = p[:, :, 0], p[:, :, 1], p[:, :, 2]

        is_green = (
            (g >= r * 1.4) &
            (g >= b * 1.4) &
            (g >= 80)
        )

        green_pixels = int(np.sum(is_green))
        print(f"Green pixel count: {green_pixels}")
        return bright_pixels > 29000 and bright_pixels<35000 and green_pixels > 18000
    
    def _get_cart_position(self) -> Tuple[int, int]:
        """Use template matching to find loot cart position"""
        coords = self.coordinate_mapper.get_coordinates()
        print("AAAAAAAAAAAAAAAAAAA")
        template = cv.imread('cart.png', cv.IMREAD_GRAYSCALE)
        if template is None:
            self.logger.error("Cart template image not found")
            return(int(coords['loot_cart']['x']), int(coords['loot_cart']['y']))
        
        screenshot = np.array(ImageGrab.grab().convert('L'))
        res = cv.matchTemplate(screenshot, template, cv.TM_SQDIFF_NORMED)

        min_val, _, min_loc, _ = cv.minMaxLoc(res)
        
        if min_val < 0.5:  # Threshold for a good match
            cart_x = min_loc[0] + template.shape[1] // 2
            cart_y = min_loc[1] + template.shape[0] // 2
            self.logger.info(f"Found loot cart at ({cart_x}, {cart_y}) with match value {min_val}")
            return (cart_x, cart_y)
        else:
            self.logger.info(f"No good match for loot cart found (min_val={min_val}), using default coordinates")
            return (coords['loot_cart']['x'], coords['loot_cart']['y'])


    def _execute_attack_sequence(self) -> bool:
        """Execute the complete attack sequence following your exact process"""
        try:
            coords = self.coordinate_mapper.get_coordinates()

            time.sleep(2)
            # Step 0 .-. : collect loot cart
            self.collect_loot()

            # Step 1: Click attack button
            if 'attack' not in coords:
                self.logger.error("Attack button not mapped")
                return False
                
            attack_coord = coords['attack']
            self.logger.info(f"1️⃣ Clicking attack button at ({attack_coord['x']}, {attack_coord['y']})")
            pyautogui.click(attack_coord['x'], attack_coord['y'])
            time.sleep(2)  # Wait for attack screen
            
            # Step 2-6: Find good loot target
            if not self._find_good_loot_target():
                self.logger.warning("Could not find good loot target")
                return False
            
            # Step 7: Start attack recording (only after good loot found)
            session_name = self._get_next_attack_session()
            self.logger.info(f"🎯 Starting attack with session: {session_name}")
            
            if not self.attack_player.play_attack(session_name, speed=1.0):
                self.logger.error("Failed to start attack recording")
                return False
            
            self.logger.info("✅ Attack recording started - troops deploying...")
            
            saftey_counter = 0
            # Step 8: wait for phase 1 to start and end
            while saftey_counter < 60:  # Safety counter to prevent infinite loop
                self.logger.info("Waiting for battle to start")
                if not self._check_phase1_ended():
                    self.logger.info("Phase 1 started")
                    break
                time.sleep(5)
                saftey_counter += 1

            saftey_counter = 0
            while saftey_counter < 60:  # Safety counter to prevent infinite loop
                self.logger.info("Waiting for battle to complete")
                if self._check_phase1_ended():
                    self.logger.info("Phase 1 done")
                    break
                time.sleep(5)
                saftey_counter += 1


            # check if there is a 2nd phase
            time.sleep(5)
            if not self._check_attack_finished():
                self.logger.info("attacking 2nd base...")
                pyautogui.moveTo(2037, 369)
                time.sleep(0.2)
                pyautogui.press('q')
                time.sleep(0.2)
                pyautogui.press('q')
                time.sleep(0.2)
                pyautogui.press('q')
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.moveTo(1608, 1318)
                time.sleep(0.1)
                pyautogui.click(1608, 1318)
                time.sleep(0.2)
                pyautogui.moveTo(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)
                time.sleep(0.2)
                pyautogui.click(2037, 369)


            saftey_counter = 0
            while saftey_counter < 60:  # Safety counter to prevent infinite loop
                self.logger.info("Waiting for battle to complete")
                if self._check_attack_finished():
                    self.logger.info("✅ Battle appears to be finished")
                    break
                time.sleep(5)  # Check every 5 seconds
                saftey_counter += 1
            # Step 9: Return home
            self._return_home()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Attack sequence failed: {e}")
            return False
    
    def _find_good_loot_target(self) -> bool:
        """Find target with good loot following exact process"""
        coords = self.coordinate_mapper.get_coordinates()
        
        if 'find_a_match' not in coords:
            self.logger.error("find_a_match button not mapped")
            return False
        
        if 'next_button' not in coords:
            self.logger.error("next_button not mapped")
            return False
        
        search_attempts = 0
        max_attempts = self.max_search_attempts
        
        while search_attempts < max_attempts and self.is_running:
            search_attempts += 1
            
            # Step 2: Click find_a_match
            find_coord = coords['find_a_match']
            self.logger.info(f"2️⃣ Clicking find_a_match at ({find_coord['x']}, {find_coord['y']}) - Attempt {search_attempts}/{max_attempts}")
            pyautogui.click(find_coord['x'], find_coord['y'])
            
            # Step 3: Wait 5 seconds
            self.logger.info("3️⃣ Waiting 5 seconds for base to load...")
            time.sleep(5)
            
            # Step 4: Check loot
            screenshot_path = self.screen_capture.capture_game_screen()
            if not screenshot_path:
                self.logger.warning("Could not take screenshot, skipping base...")
                continue # Try again

            use_ai = self.config.get('ai_analyzer.enabled', False)
            self.logger.info(f"AI Analysis is {'ENABLED' if use_ai else 'DISABLED'}.")

            decision_to_attack = False
            if use_ai:
                self.logger.info("4️⃣ Checking enemy loot with AI...")
                decision_to_attack = self._check_loot_with_ai(screenshot_path)
            else:
                self.logger.info("4️⃣ Performing simple loot check (AI Disabled)...")
                decision_to_attack = True #self._check_loot()

            if decision_to_attack:
                self.logger.info("✅ Base is good! Proceeding with attack!")
                return True
            else:
                # Step 5: Bad loot or AI said SKIP, click next
                self.logger.info("❌ Base not suitable. Clicking next...")
                if 'next_button' in coords:
                    next_coord = coords['next_button']
                    pyautogui.click(next_coord['x'], next_coord['y'])
                    time.sleep(3)  # Wait before next search
                else:
                    self.logger.error("next_button not mapped, cannot skip.")
                    return False
        
        self.logger.warning(f"Could not find good loot after {max_attempts} attempts")
        
        # Click end button and retry the entire search process
        self.logger.info("🔄 No good bases found - clicking end button to restart search...")
        self._click_end_button_and_retry()
        
        # Try one more complete search cycle
        self.logger.info("🔄 Retrying base search after end button...")
        return self._search_for_good_base_cycle()
        
    def _search_for_good_base_cycle(self) -> bool:
        """Perform one complete cycle of base searching"""
        coords = self.coordinate_mapper.get_coordinates()
        
        if 'find_a_match' not in coords or 'next_button' not in coords:
            self.logger.error("Required buttons not mapped for base search")
            return False
        
        search_attempts = 0
        max_attempts = self.max_search_attempts
        
        while search_attempts < max_attempts and self.is_running:
            search_attempts += 1
            
            # Click find_a_match
            find_coord = coords['find_a_match']
            self.logger.info(f"2️⃣ Clicking find_a_match at ({find_coord['x']}, {find_coord['y']}) - Attempt {search_attempts}/{max_attempts}")
            pyautogui.click(find_coord['x'], find_coord['y'])
            
            # Wait for base to load
            self.logger.info("3️⃣ Waiting 5 seconds for base to load...")
            time.sleep(5)
            
            # Check loot
            screenshot_path = self.screen_capture.capture_game_screen()
            if not screenshot_path:
                self.logger.warning("Could not take screenshot, skipping base...")
                continue
            
            use_ai = self.config.get('ai_analyzer.enabled', False)
            self.logger.info(f"AI Analysis is {'ENABLED' if use_ai else 'DISABLED'}.")
            
            decision_to_attack = False
            if use_ai:
                self.logger.info("4️⃣ Checking enemy loot with AI...")
                decision_to_attack = self._check_loot_with_ai(screenshot_path)
            else:
                self.logger.info("4️⃣ Performing simple loot check (AI Disabled)...")
                decision_to_attack = self._check_loot()
            
            if decision_to_attack:
                self.logger.info("✅ Base is good! Proceeding with attack!")
                return True
            else:
                # Bad base, click next
                self.logger.info("❌ Base not suitable. Clicking next...")
                next_coord = coords['next_button']
                pyautogui.click(next_coord['x'], next_coord['y'])
                time.sleep(3)
        
        return False
    
    def _check_loot_with_ai(self, screenshot_path: str) -> bool:
        """Analyze the base with Gemini and decide whether to attack."""
        min_gold = self.config.get('ai_analyzer.min_gold', 300000)
        min_elixir = self.config.get('ai_analyzer.min_elixir', 300000)
        min_dark = self.config.get('ai_analyzer.min_dark_elixir', 5000)

        analysis = self.ai_analyzer.analyze_base(screenshot_path, min_gold, min_elixir, min_dark)

        if analysis.get("error"):
            self.logger.error(f"AI analysis failed: {analysis['reasoning']}")
            return False

        # Log detailed loot comparison for debugging
        loot = analysis.get("loot", {})
        extracted_gold = loot.get("gold", 0)
        extracted_elixir = loot.get("elixir", 0)
        extracted_dark = loot.get("dark_elixir", 0)
        townhall_level = analysis.get("townhall_level", 0)
        
        self.logger.info(f"🔍 AI Extracted Loot: Gold={extracted_gold:,}, Elixir={extracted_elixir:,}, Dark={extracted_dark:,}")
        self.logger.info(f"🏰 Town Hall Level: {townhall_level}")
        self.logger.info(f"📋 Requirements: Gold={min_gold:,}, Elixir={min_elixir:,}, Dark={min_dark:,}, Max TH=12")
        
        # Check loot requirements
        gold_ok = extracted_gold >= min_gold
        elixir_ok = extracted_elixir >= min_elixir
        dark_ok = extracted_dark >= min_dark
        th_ok = townhall_level <= 12
        
        self.logger.info(f"✅/❌ Meets Requirements: Gold={gold_ok}, Elixir={elixir_ok}, Dark={dark_ok}, TH_Level={th_ok}")
        
        # Override AI decision if Town Hall is too high
        if townhall_level > 12:
            self.logger.info(f"❌ Overriding AI: Town Hall {townhall_level} is too strong (max allowed: 12)")
            return False

        recommendation = analysis.get("recommendation", "SKIP").upper()
        return recommendation == "ATTACK"

    def _check_loot(self) -> bool:
        """Check if enemy base has good loot"""
        coords = self.coordinate_mapper.get_coordinates()
        
        # Check each loot type
        loot_checks = {
            'gold': ('enemy_gold', self.config.get('ai_analyzer.min_gold', 300000)),
            'elixir': ('enemy_elixir', self.config.get('ai_analyzer.min_elixir', 300000)),
            'dark': ('enemy_dark_elixir', self.config.get('ai_analyzer.min_dark_elixir', 5000))
        }
        
        good_loot_count = 0
        
        for loot_name, (coord_name, min_value) in loot_checks.items():
            if coord_name in coords:
                coord = coords[coord_name]
                self.logger.info(f"Checking {loot_name} at ({coord['x']}, {coord['y']})")
                
                # Simple check - in real game you'd use OCR here
                # For now, assume good loot (you can implement OCR later)
                has_good_loot = True  # Placeholder
                
                if has_good_loot:
                    good_loot_count += 1
                    self.logger.info(f"✅ {loot_name.capitalize()}: Good")
                else:
                    self.logger.info(f"❌ {loot_name.capitalize()}: Too low")
        
        # Require at least 2 out of 3 loot types to be good
        is_good = good_loot_count >= 2
        
        if is_good:
            self.logger.info(f"✅ Loot check PASSED - {good_loot_count}/3 loot types are good")
        else:
            self.logger.info(f"❌ Loot check FAILED - Only {good_loot_count}/3 loot types are good")
        
        return is_good
    
    def _click_end_button_and_retry(self) -> None:
        """Click end button when Town Hall is not detected and retry"""
        coords = self.coordinate_mapper.get_coordinates()
        
        if 'end_button' in coords:
            end_coord = coords['end_button']
            self.logger.info(f"🔄 Clicking end_button at ({end_coord['x']}, {end_coord['y']})")
            pyautogui.click(end_coord['x'], end_coord['y'])
            time.sleep(3)  # Wait for end action to complete
        else:
            self.logger.warning("end_button not mapped - cannot retry automatically")
    
    def _return_home(self) -> None:
        """Return to home base after battle"""
        coords = self.coordinate_mapper.get_coordinates()
        
        self.logger.info("🏠 Returning to home base...")
        
        # Only click return_home button
        if 'return_home' in coords:
            home_coord = coords['return_home']
            self.logger.info(f"Clicking return_home at ({home_coord['x']}, {home_coord['y']})")
            pyautogui.click(home_coord['x'], home_coord['y'])
            time.sleep(5)  # Wait to return home
        else:
            self.logger.warning("return_home button not mapped")
        
        self.logger.info("✅ Returned to home base")
    
    def _get_next_attack_session(self) -> str:
        """Get the next attack session from rotation"""
        if not self.attack_sessions:
            return ""
        
        session = self.attack_sessions[self.current_session_index]
        self.current_session_index = (self.current_session_index + 1) % len(self.attack_sessions)
        return session
    
    def get_stats(self) -> Dict:
        """Get automation statistics"""
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            runtime_hours = runtime.total_seconds() / 3600
        else:
            runtime_hours = 0
        
        return {
            'is_running': self.is_running,
            'total_attacks': self.stats['total_attacks'],
            'successful_attacks': self.stats['successful_attacks'],
            'failed_attacks': self.stats['failed_attacks'],
            'success_rate': (self.stats['successful_attacks'] / max(self.stats['total_attacks'], 1)) * 100,
            'runtime_hours': runtime_hours,
            'attacks_per_hour': self.stats['total_attacks'] / max(runtime_hours, 1),
            'last_attack': self.stats['last_attack_time'].strftime("%H:%M:%S") if self.stats['last_attack_time'] else "None",
            'configured_sessions': self.attack_sessions.copy()
        }
    
    def update_loot_requirements(self, min_gold: int = None, min_elixir: int = None, min_dark_elixir: int = None):
        """Update minimum loot requirements"""
        if min_gold is not None:
            self.config.set('ai_analyzer.min_gold', min_gold)
        if min_elixir is not None:
            self.config.set('ai_analyzer.min_elixir', min_elixir)
        if min_dark_elixir is not None:
            self.config.set('ai_analyzer.min_dark_elixir', min_dark_elixir)
        
        self.logger.info(f"Updated loot requirements: Gold={self.config.get('ai_analyzer.min_gold')}, Elixir={self.config.get('ai_analyzer.min_elixir')}, Dark={self.config.get('ai_analyzer.min_dark_elixir')}")
    
    def configure_buttons(self) -> Dict[str, str]:
        """Get list of required button mappings for the simplified automation"""
        return {
            'attack': 'Main attack button on home screen',
            'find_a_match': 'Find match/search button in attack screen',
            'next_button': 'Next button to skip bases with low loot',
            'return_home': 'Return home button after battle completion',
            'enemy_gold': 'Enemy gold display for loot checking',
            'enemy_elixir': 'Enemy elixir display for loot checking',
            'enemy_dark_elixir': 'Enemy dark elixir display for loot checking'
        }
    
 