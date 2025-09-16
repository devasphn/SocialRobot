# face_animation/face.py
import pygame
import sys
import queue
import os

class FaceAnimator:
    def __init__(self, face_image_path, mouth_image_path,
                 window_size=(1920, 1080),  # Updated to projector resolution
                 min_scale=1.0, max_scale=2.5):
        self.face_image_path = face_image_path
        self.mouth_image_path = mouth_image_path
        self.window_size = window_size
        self.min_scale = min_scale
        self.max_scale = max_scale
        
        self._amplitude_queue = queue.Queue()
        self.running = True
        
        # Store the calibrated positions from our alignment tests
        self.face_x_offset = -300
        self.face_y_offset = 0
        self.face_scale = 0.8
        self.face_rotation = 180
        
        self.mouth_x_offset = 0
        self.mouth_y_offset = 0
        self.mouth_base_scale = 1.0
        self.mouth_rotation = 180
        
    def update_amplitude(self, ampl):
        self._amplitude_queue.put(ampl)
    
    def run(self):
        pygame.init()
        
        # Set fullscreen for projector
        # Uncomment the next line for fullscreen mode on the projector
        # self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        # For testing, use windowed mode:
        self.screen = pygame.display.set_mode(self.window_size)
        
        pygame.display.set_caption("Robot Face")
        
        # Get actual screen dimensions (useful for fullscreen)
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()
        
        # Load and transform face image with calibrated settings
        self.face_img = pygame.image.load(self.face_image_path).convert_alpha()
        
        # Apply scale
        face_width = int(self.face_img.get_width() * self.face_scale)
        face_height = int(self.face_img.get_height() * self.face_scale)
        self.face_img = pygame.transform.scale(self.face_img, (face_width, face_height))
        
        # Apply rotation (180 degrees)
        self.face_img = pygame.transform.rotate(self.face_img, -self.face_rotation)  # Negative for clockwise
        
        # Position face with calibrated offset
        self.face_rect = self.face_img.get_rect(
            center=(screen_width // 2 + self.face_x_offset,
                   screen_height // 2 + self.face_y_offset)
        )
        
        # Load and transform mouth image
        self.mouth_img_original = pygame.image.load(self.mouth_image_path).convert_alpha()
        
        # Apply base scale to mouth
        mouth_width = int(self.mouth_img_original.get_width() * self.mouth_base_scale)
        mouth_height = int(self.mouth_img_original.get_height() * self.mouth_base_scale)
        self.mouth_img_base = pygame.transform.scale(self.mouth_img_original, (mouth_width, mouth_height))
        
        # Apply rotation to mouth (180 degrees)
        self.mouth_img_base = pygame.transform.rotate(self.mouth_img_base, -self.mouth_rotation)  # Negative for clockwise
        
        # Store base mouth dimensions for scaling during animation
        self.mouth_base_width = self.mouth_img_base.get_width()
        self.mouth_base_height = self.mouth_img_base.get_height()
        
        # Mouth center position with calibrated offset
        self.mouth_center_x = screen_width // 2 + self.mouth_x_offset
        self.mouth_center_y = screen_height // 2 + self.mouth_y_offset
        
        self.clock = pygame.time.Clock()
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        break
            
            # Clear screen (black background)
            self.screen.fill((0, 0, 0))
            
            # Draw face
            self.screen.blit(self.face_img, self.face_rect)
            
            # Calculate mouth scale based on amplitude
            scale_factor = self.min_scale
            if not self._amplitude_queue.empty():
                amplitude = self._amplitude_queue.get_nowait()
                # Map amplitude to scale (adjust the divisor as needed for sensitivity)
                mapped_scale = self.min_scale + (amplitude / 2000.0) * (self.max_scale - self.min_scale)
                scale_factor = max(self.min_scale, min(mapped_scale, self.max_scale))
            
            # Scale mouth for animation (relative to base scale)
            new_w = int(self.mouth_base_width * scale_factor)
            new_h = int(self.mouth_base_height * scale_factor)
            mouth_scaled = pygame.transform.scale(self.mouth_img_base, (new_w, new_h))
            
            # Position scaled mouth at calibrated center
            scaled_rect = mouth_scaled.get_rect(
                center=(self.mouth_center_x, self.mouth_center_y)
            )
            
            # Draw mouth
            self.screen.blit(mouth_scaled, scaled_rect)
            
            pygame.display.flip()
            self.clock.tick(30)
        
        pygame.quit()
    
    def stop(self):
        self.running = False