import pygame
import random
import sqlite3
import json
from datetime import datetime
import matplotlib.pyplot as plt
from collections import deque

# Initialize Pygame
pygame.init()

# Game Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
GAME_WIDTH = 600
GAME_HEIGHT = 600
CELL_SIZE = 20
CELLS_X = GAME_WIDTH // CELL_SIZE
CELLS_Y = GAME_HEIGHT // CELL_SIZE

# Colors
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
DARK_GREEN = (0, 200, 0)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('snake_stats.db')
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT,
                score INTEGER,
                time_alive REAL,
                max_speed REAL,
                food_eaten INTEGER,
                game_date TEXT,
                movements INTEGER,
                efficiency REAL
            )
        ''')
        self.conn.commit()
    
    def save_game_stats(self, stats):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO game_stats 
            (player_name, score, time_alive, max_speed, food_eaten, game_date, movements, efficiency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', stats)
        self.conn.commit()
    
    def get_player_stats(self, player_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM game_stats WHERE player_name = ? ORDER BY game_date DESC
        ''', (player_name,))
        return cursor.fetchall()
    
    def get_top_scores(self, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT player_name, score, time_alive FROM game_stats 
            ORDER BY score DESC LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

class GameAnalytics:
    def __init__(self):
        self.start_time = None
        self.movements = 0
        self.food_eaten = 0
        self.max_speed = 0
        self.speed_history = deque(maxlen=100)
    
    def start_game(self):
        self.start_time = datetime.now()
        self.movements = 0
        self.food_eaten = 0
        self.max_speed = 0
        self.speed_history.clear()
    
    def record_movement(self):
        self.movements += 1
    
    def record_food_eaten(self):
        self.food_eaten += 1
    
    def record_speed(self, speed):
        self.speed_history.append(speed)
        self.max_speed = max(self.max_speed, speed)
    
    def get_game_duration(self):
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0
    
    def calculate_efficiency(self):
        if self.movements > 0:
            return (self.food_eaten / self.movements) * 100
        return 0

class Snake:
    def __init__(self):
        self.positions = [(CELLS_X // 2, CELLS_Y // 2)]
        self.direction = (1, 0)
        self.grow = False
    
    def move(self):
        head_x, head_y = self.positions[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])
        
        self.positions.insert(0, new_head)
        
        if not self.grow:
            self.positions.pop()
        else:
            self.grow = False
    
    def change_direction(self, new_direction):
        # Prevent snake from moving into itself
        if (new_direction[0] * -1, new_direction[1] * -1) != self.direction:
            self.direction = new_direction
    
    def grow_snake(self):
        self.grow = True
    
    def check_collision(self):
        head = self.positions[0]
        
        # Check wall collision
        if (head[0] < 0 or head[0] >= CELLS_X or 
            head[1] < 0 or head[1] >= CELLS_Y):
            return True
        
        # Check self collision
        if head in self.positions[1:]:
            return True
        
        return False
    
    def draw(self, surface):
        for i, pos in enumerate(self.positions):
            x, y = pos[0] * CELL_SIZE, pos[1] * CELL_SIZE
            color = DARK_GREEN if i == 0 else GREEN
            pygame.draw.rect(surface, color, (x, y, CELL_SIZE, CELL_SIZE))
            pygame.draw.rect(surface, WHITE, (x, y, CELL_SIZE, CELL_SIZE), 1)

class Food:
    def __init__(self):
        self.position = self.generate_position()
    
    def generate_position(self):
        return (random.randint(0, CELLS_X - 1), random.randint(0, CELLS_Y - 1))
    
    def respawn(self, snake_positions):
        while True:
            new_pos = self.generate_position()
            if new_pos not in snake_positions:
                self.position = new_pos
                break
    
    def draw(self, surface):
        x, y = self.position[0] * CELL_SIZE, self.position[1] * CELL_SIZE
        pygame.draw.rect(surface, RED, (x, y, CELL_SIZE, CELL_SIZE))

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Snake Game with Analytics")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.snake = Snake()
        self.food = Food()
        self.db = Database()
        self.analytics = GameAnalytics()
        
        self.score = 0
        self.speed = 5
        self.running = True
        self.game_over = False
        self.player_name = "Player1"
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if not self.game_over:
                    if event.key == pygame.K_UP:
                        self.snake.change_direction((0, -1))
                        self.analytics.record_movement()
                    elif event.key == pygame.K_DOWN:
                        self.snake.change_direction((0, 1))
                        self.analytics.record_movement()
                    elif event.key == pygame.K_LEFT:
                        self.snake.change_direction((-1, 0))
                        self.analytics.record_movement()
                    elif event.key == pygame.K_RIGHT:
                        self.snake.change_direction((1, 0))
                        self.analytics.record_movement()
                else:
                    if event.key == pygame.K_r:
                        self.restart_game()
                    elif event.key == pygame.K_a:
                        self.show_analytics()
    
    def update(self):
        if not self.game_over:
            self.snake.move()
            self.analytics.record_speed(self.speed)
            
            # Check food collision
            if self.snake.positions[0] == self.food.position:
                self.score += 10
                self.snake.grow_snake()
                self.food.respawn(self.snake.positions)
                self.analytics.record_food_eaten()
                
                # Increase speed every 5 foods
                if self.score % 50 == 0:
                    self.speed += 1
            
            # Check game over
            if self.snake.check_collision():
                self.game_over = True
                self.save_game_stats()
    
    def save_game_stats(self):
        game_duration = self.analytics.get_game_duration()
        efficiency = self.analytics.calculate_efficiency()
        
        stats = (
            self.player_name,
            self.score,
            game_duration,
            self.analytics.max_speed,
            self.analytics.food_eaten,
            datetime.now().isoformat(),
            self.analytics.movements,
            efficiency
        )
        
        self.db.save_game_stats(stats)
    
    def restart_game(self):
        self.snake = Snake()
        self.food = Food()
        self.analytics = GameAnalytics()
        self.analytics.start_game()
        self.score = 0
        self.speed = 5
        self.game_over = False
    
    def show_analytics(self):
        """Display analytics using matplotlib"""
        try:
            stats = self.db.get_player_stats(self.player_name)
            if not stats:
                print("No game data found!")
                return
            
            # Extract data for plotting
            scores = [stat[2] for stat in stats[-10:]]  # Last 10 games
            times = [stat[3] for stat in stats[-10:]]
            efficiencies = [stat[8] for stat in stats[-10:]]
            
            # Create subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle(f'Game Analytics for {self.player_name}', fontsize=16)
            
            # Score progression
            ax1.plot(scores, marker='o', color='blue')
            ax1.set_title('Score Progression (Last 10 Games)')
            ax1.set_xlabel('Game Number')
            ax1.set_ylabel('Score')
            ax1.grid(True)
            
            # Time alive
            ax2.plot(times, marker='s', color='green')
            ax2.set_title('Survival Time (Last 10 Games)')
            ax2.set_xlabel('Game Number')
            ax2.set_ylabel('Time (seconds)')
            ax2.grid(True)
            
            # Efficiency
            ax3.bar(range(len(efficiencies)), efficiencies, color='orange')
            ax3.set_title('Movement Efficiency (%)')
            ax3.set_xlabel('Game Number')
            ax3.set_ylabel('Efficiency')
            
            # High scores leaderboard data
            top_scores = self.db.get_top_scores(5)
            if top_scores:
                names = [score[0] for score in top_scores]
                values = [score[1] for score in top_scores]
                ax4.barh(names, values, color='red')
                ax4.set_title('Top 5 High Scores')
                ax4.set_xlabel('Score')
            
            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            print(f"Error displaying analytics: {e}")
    
    def draw_game_area(self):
        # Draw game area background
        game_rect = pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT)
        pygame.draw.rect(self.screen, BLACK, game_rect)
        pygame.draw.rect(self.screen, WHITE, game_rect, 2)
    
    def draw_sidebar(self):
        # Draw sidebar background
        sidebar_rect = pygame.Rect(GAME_WIDTH, 0, WINDOW_WIDTH - GAME_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, GRAY, sidebar_rect)
        
        # Draw stats
        y_offset = 20
        stats_text = [
            f"Score: {self.score}",
            f"Speed: {self.speed}",
            f"Length: {len(self.snake.positions)}",
            f"Time: {self.analytics.get_game_duration():.1f}s",
            f"Moves: {self.analytics.movements}",
            f"Efficiency: {self.analytics.calculate_efficiency():.1f}%"
        ]
        
        for text in stats_text:
            rendered = self.small_font.render(text, True, WHITE)
            self.screen.blit(rendered, (GAME_WIDTH + 10, y_offset))
            y_offset += 25
        
        # Instructions
        if not self.game_over:
            instructions = ["Use arrow keys to move", "Eat red food to grow"]
        else:
            instructions = ["Press R to restart", "Press A for analytics"]
        
        y_offset += 50
        for instruction in instructions:
            rendered = self.small_font.render(instruction, True, WHITE)
            self.screen.blit(rendered, (GAME_WIDTH + 10, y_offset))
            y_offset += 25
    
    def draw(self):
        self.screen.fill(WHITE)
        self.draw_game_area()
        self.draw_sidebar()
        
        if not self.game_over:
            self.snake.draw(self.screen)
            self.food.draw(self.screen)
        else:
            # Game over screen
            game_over_text = self.font.render("GAME OVER", True, RED)
            score_text = self.font.render(f"Final Score: {self.score}", True, WHITE)
            restart_text = self.small_font.render("Press R to restart or A for analytics", True, WHITE)
            
            game_rect = pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT)
            
            # Center the text
            game_over_rect = game_over_text.get_rect(center=(GAME_WIDTH//2, GAME_HEIGHT//2 - 40))
            score_rect = score_text.get_rect(center=(GAME_WIDTH//2, GAME_HEIGHT//2))
            restart_rect = restart_text.get_rect(center=(GAME_WIDTH//2, GAME_HEIGHT//2 + 40))
            
            self.screen.blit(game_over_text, game_over_rect)
            self.screen.blit(score_text, score_rect)
            self.screen.blit(restart_text, restart_rect)
        
        pygame.display.flip()
    
    def run(self):
        self.analytics.start_game()
        
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.speed)
        
        pygame.quit()

if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Please install matplotlib: pip install matplotlib")
        exit(1)
    
    game = Game()
    game.run()
