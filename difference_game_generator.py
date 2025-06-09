import os
import random
import json
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np
from datetime import datetime
import uuid

class DifferenceGameGenerator:
    def __init__(self):
        self.difficulty_configs = {
            50: {
                'color_shift_range': (30, 80),
                'size_change_range': (0.3, 0.7),
                'blur_intensity': (0, 1),
                'position_shift': (10, 30),
                'opacity_change': (0.3, 0.8)
            },
            60: {
                'color_shift_range': (20, 50),
                'size_change_range': (0.5, 0.8),
                'blur_intensity': (0, 0.5),
                'position_shift': (5, 20),
                'opacity_change': (0.5, 0.9)
            },
            70: {
                'color_shift_range': (10, 30),
                'size_change_range': (0.7, 0.9),
                'blur_intensity': (0, 0.3),
                'position_shift': (3, 15),
                'opacity_change': (0.7, 0.95)
            },
            80: {
                'color_shift_range': (5, 20),
                'size_change_range': (0.8, 0.95),
                'blur_intensity': (0, 0.2),
                'position_shift': (2, 10),
                'opacity_change': (0.8, 0.98)
            },
            90: {
                'color_shift_range': (2, 10),
                'size_change_range': (0.9, 0.98),
                'blur_intensity': (0, 0.1),
                'position_shift': (1, 5),
                'opacity_change': (0.9, 0.99)
            }
        }
    
    def create_base_scene(self, width=800, height=600):
        """Generate a base scene with random objects"""
        img = Image.new('RGB', (width, height), color=(135, 206, 235))  # Sky blue
        draw = ImageDraw.Draw(img)
        
        # Add background elements
        # Ground
        draw.rectangle([0, height-100, width, height], fill=(34, 139, 34))
        
        # Sun
        sun_x, sun_y = random.randint(50, width-50), random.randint(50, 150)
        draw.ellipse([sun_x-30, sun_y-30, sun_x+30, sun_y+30], fill=(255, 255, 0))
        
        # Clouds
        for _ in range(random.randint(2, 4)):
            cloud_x = random.randint(50, width-100)
            cloud_y = random.randint(50, 200)
            draw.ellipse([cloud_x, cloud_y, cloud_x+60, cloud_y+30], fill=(255, 255, 255))
            draw.ellipse([cloud_x+20, cloud_y-10, cloud_x+80, cloud_y+20], fill=(255, 255, 255))
        
        # Trees
        for _ in range(random.randint(3, 6)):
            tree_x = random.randint(50, width-50)
            tree_y = height - 100
            # Trunk
            draw.rectangle([tree_x-10, tree_y-60, tree_x+10, tree_y], fill=(139, 69, 19))
            # Leaves
            draw.ellipse([tree_x-25, tree_y-90, tree_x+25, tree_y-40], fill=(0, 128, 0))
        
        # Houses
        for _ in range(random.randint(1, 3)):
            house_x = random.randint(100, width-150)
            house_y = height - 100
            # House body
            draw.rectangle([house_x, house_y-80, house_x+80, house_y], fill=(205, 133, 63))
            # Roof
            draw.polygon([house_x-10, house_y-80, house_x+90, house_y-80, house_x+40, house_y-120], fill=(139, 0, 0))
            # Door
            draw.rectangle([house_x+30, house_y-40, house_x+50, house_y], fill=(101, 67, 33))
            # Windows
            draw.rectangle([house_x+10, house_y-60, house_x+25, house_y-45], fill=(173, 216, 230))
            draw.rectangle([house_x+55, house_y-60, house_x+70, house_y-45], fill=(173, 216, 230))
        
        return img
    
    def apply_difference(self, img, diff_type, intensity, position):
        """Apply a specific type of difference to the image"""
        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)
        
        x, y = position
        
        if diff_type == 'color_change':
            # Change color of a region
            color_shift = random.randint(*intensity['color_shift_range'])
            region_size = random.randint(20, 60)
            
            # Extract region and modify color
            region = img.crop((x, y, x+region_size, y+region_size))
            enhancer = ImageEnhance.Color(region)
            region = enhancer.enhance(random.uniform(0.2, 2.0))
            img_copy.paste(region, (x, y))
            
        elif diff_type == 'object_removal':
            # Remove an object by painting over it
            region_size = random.randint(30, 80)
            # Sample surrounding color and paint over
            surrounding_color = img.getpixel((x+region_size+5, y+region_size+5))
            draw.ellipse([x, y, x+region_size, y+region_size], fill=surrounding_color)
            
        elif diff_type == 'object_addition':
            # Add a new small object
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
            color = random.choice(colors)
            size = random.randint(10, 30)
            draw.ellipse([x, y, x+size, y+size], fill=color)
            
        elif diff_type == 'size_change':
            # Change size of existing element
            region_size = random.randint(40, 100)
            region = img.crop((x, y, x+region_size, y+region_size))
            
            scale_factor = random.uniform(*intensity['size_change_range'])
            new_size = (int(region_size * scale_factor), int(region_size * scale_factor))
            region = region.resize(new_size, Image.Resampling.LANCZOS)
            
            # Paste back
            img_copy.paste(region, (x, y))
            
        elif diff_type == 'position_shift':
            # Shift an object slightly
            region_size = random.randint(30, 70)
            region = img.crop((x, y, x+region_size, y+region_size))
            
            # Cover original position
            surrounding_color = img.getpixel((x+region_size+5, y+region_size+5))
            draw.rectangle([x, y, x+region_size, y+region_size], fill=surrounding_color)
            
            # Paste in new position
            shift_x = random.randint(*intensity['position_shift'])
            shift_y = random.randint(*intensity['position_shift'])
            new_x = max(0, min(img.width - region_size, x + shift_x))
            new_y = max(0, min(img.height - region_size, y + shift_y))
            img_copy.paste(region, (new_x, new_y))
        
        return img_copy
    
    def generate_game(self, difficulty_level=50, num_differences=5):
        """Generate a complete find the difference game"""
        if difficulty_level not in self.difficulty_configs:
            raise ValueError(f"Difficulty level {difficulty_level} not supported")
        
        # Create base image
        original_img = self.create_base_scene()
        modified_img = original_img.copy()
        
        # Track differences for validation
        differences = []
        intensity = self.difficulty_configs[difficulty_level]
        
        # Apply differences
        diff_types = ['color_change', 'object_removal', 'object_addition', 'size_change', 'position_shift']
        
        for i in range(num_differences):
            # Choose random position (avoid edges)
            x = random.randint(50, original_img.width - 150)
            y = random.randint(50, original_img.height - 150)
            
            # Choose difference type
            diff_type = random.choice(diff_types)
            
            # Apply difference
            modified_img = self.apply_difference(modified_img, diff_type, intensity, (x, y))
            
            differences.append({
                'type': diff_type,
                'position': (x, y),
                'id': i + 1
            })
        
        # Create game data
        game_data = {
            'game_id': str(uuid.uuid4()),
            'difficulty': difficulty_level,
            'differences': differences,
            'created_at': datetime.now().isoformat(),
            'total_differences': num_differences
        }
        
        return {
            'original_image': original_img,
            'modified_image': modified_img,
            'game_data': game_data
        }
    
    def save_game(self, game_result, output_dir='games'):
        """Save game images and data to files"""
        os.makedirs(output_dir, exist_ok=True)
        
        game_id = game_result['game_data']['game_id']
        difficulty = game_result['game_data']['difficulty']
        
        # Save images
        original_path = f"{output_dir}/{game_id}_original.png"
        modified_path = f"{output_dir}/{game_id}_modified.png"
        data_path = f"{output_dir}/{game_id}_data.json"
        
        game_result['original_image'].save(original_path)
        game_result['modified_image'].save(modified_path)
        
        # Save game data
        with open(data_path, 'w') as f:
            json.dump(game_result['game_data'], f, indent=2)
        
        return {
            'original_path': original_path,
            'modified_path': modified_path,
            'data_path': data_path,
            'game_id': game_id,
            'difficulty': difficulty
        }

# Example usage and testing
def generate_test_games():
    """Generate sample games for testing"""
    generator = DifferenceGameGenerator()
    
    # Generate games at different difficulty levels
    difficulties = [50, 60, 70, 80, 90]
    
    for difficulty in difficulties:
        print(f"Generating game with {difficulty}% difficulty...")
        game = generator.generate_game(difficulty_level=difficulty)
        result = generator.save_game(game)
        print(f"Saved game: {result['game_id']} at difficulty {difficulty}%")
        print(f"Files: {result['original_path']}, {result['modified_path']}")
        print("---")

if __name__ == "__main__":
    # Test the generator
    generate_test_games()