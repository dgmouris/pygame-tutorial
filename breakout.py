import random
from datetime import datetime, timedelta

import os
import time
import pygame
from pygame.rect import Rect

from ball import Ball
from brick import Brick
from button import Button
from game import Game
from paddle import Paddle
from text_object import TextObject
import colors

import config


special_effects = dict(
    long_paddle=(
        colors.ORANGE,
        lambda g: g.paddle.bounds.inflate_ip(
                    config.paddle_width // 2, 0),
        lambda g: g.paddle.bounds.inflate_ip(
                    -config.paddle_width // 2, 0)),
    slow_ball=(
        colors.AQUAMARINE2,
        lambda g: g.change_ball_speed(-1),
        lambda g: g.change_ball_speed(1)),
    tripple_points=(
        colors.DARKSEAGREEN4,
        lambda g: g.set_points_per_brick(3),
        lambda g: g.set_points_per_brick(1)),
    extra_life=(
        colors.GOLD1,
        lambda g: g.add_life(),
        lambda g: None))


class Breakout(Game):
    def __init__(self):
        Game.__init__(self, 'Breakout', config.screen_width, config.screen_height, config.background_image, config.frame_rate)
        self.sound_effects = {name: pygame.mixer.Sound(sound) for name, sound in config.sounds_effects.items()}
        self.reset_effect = None
        self.effect_start_time = None
        self.score = 0
        self.lives = config.initial_lives
        self.start_level = False
        self.paddle = None
        self.bricks = None
        self.ball = None
        self.menu_buttons = []
        self.is_game_running = False
        self.create_objects()
        self.points_per_brick = 1

    def show_message(self,
                     text,
                     color=colors.WHITE,
                     font_name='Arial',
                     font_size=20,
                     centralized=False):
        message = TextObject(config.screen_width // 2,
                             config.screen_height // 2,
                             lambda: text, color,
                             font_name, font_size)
        self.draw()
        message.draw(self.surface, centralized)
        pygame.display.update()
        time.sleep(config.message_duration)

    def add_life(self):
        self.lives += 1

    def set_points_per_brick(self, points):
        self.points_per_brick = points

    def change_ball_speed(self, dy):
        self.ball.speed = (self.ball.speed[0], self.ball.speed[1] + dy)

    def handle_ball_collisions(self):
        def intersect(obj, ball):
            edges = dict(
                left=Rect(obj.left, obj.top, 1, obj.height),
                right=Rect(obj.right, obj.top, 1, obj.height),
                top=Rect(obj.left, obj.top, obj.width, 1),
                bottom=Rect(obj.left, obj.bottom, obj.width, 1))
            collisions = set(edge for edge, rect in edges.items() if
                             ball.bounds.colliderect(rect))
            if not collisions:
                return None

            if len(collisions) == 1:
                return list(collisions)[0]

            if 'top' in collisions:
                if ball.centery >= obj.top:
                    return 'top'
                if ball.centerx < obj.left:
                    return 'left'
                else:
                    return 'right'

            if 'bottom' in collisions:
                if ball.centery >= obj.bottom:
                    return 'bottom'
                if ball.centerx < obj.left:
                    return 'left'
                else:
                    return 'right'

        # Hit paddle
        s = self.ball.speed
        edge = intersect(self.paddle, self.ball)
        if edge is not None:
            self.sound_effects['paddle_hit'].play()
        if edge == 'top':
            speed_x = s[0]
            speed_y = -s[1]
            if self.paddle.moving_left:
                speed_x -= 1
            elif self.paddle.moving_left:
                speed_x += 1
            self.ball.speed = speed_x, speed_y
        elif edge in ('left', 'right'):
            self.ball.speed = (-s[0], s[1])

        # Hit floor
        if self.ball.top > config.screen_height:
            self.lives -= 1
            if self.lives == 0:
                self.game_over = True
            else:
                self.create_ball()

        # Hit ceiling
        if self.ball.top < 0:
            self.ball.speed = (s[0], -s[1])

        # Hit wall
        if self.ball.left < 0 or self.ball.right > config.screen_width:
            self.ball.speed = (-s[0], s[1])

        # Hit brick
        for brick in self.bricks:
            edge = intersect(brick, self.ball)
            if not edge:
                continue

            self.bricks.remove(brick)
            self.objects.remove(brick)
            self.score += self.points_per_brick

            if edge in ('top', 'bottom'):
                self.ball.speed = (s[0], -s[1])
            else:
                self.ball.speed = (-s[0], s[1])

            if brick.special_effect is not None:
                # Reset previous effect if any
                if self.reset_effect is not None:
                    self.reset_effect(self)

                # Trigger special effect
                self.effect_start_time = datetime.now()
                brick.special_effect[0](self)
                # Set current reset effect function
                self.reset_effect = brick.special_effect[1]

    def create_menu(self):
        def on_play(button):
            for b in self.menu_buttons:
                self.objects.remove(b)

            self.is_game_running = True
            self.start_level = True

        def on_quit(button):
            self.game_over = True
            self.is_game_running = False
            self.game_over = True

        for i, (text, click_handler) in enumerate((('PLAY', on_play), ('QUIT', on_quit))):
            b = Button(config.menu_offset_x,
                       config.menu_offset_y + (config.menu_button_h + 5) * i,
                       config.menu_button_w,
                       config.menu_button_h,
                       text,
                       click_handler,
                       padding=5)
            self.objects.append(b)
            self.menu_buttons.append(b)
            self.mouse_handlers.append(b.handle_mouse_event)

    def create_objects(self):
        self.create_bricks()
        self.create_paddle()
        self.create_ball()
        self.create_labels()
        self.create_menu()

    def create_ball(self):
        speed = (random.randint(-2, 2), config.ball_speed)
        self.ball = Ball(config.screen_width // 2,
                         config.screen_height // 2,
                         config.ball_radius,
                         config.ball_color,
                         speed)
        self.objects.append(self.ball)

    def create_labels(self):
        self.score_label = TextObject(config.score_offset,
                                      config.status_offset_y,
                                      lambda: f'SCORE: {self.score}',
                                      config.text_color,
                                      config.font_name,
                                      config.font_size)
        self.objects.append(self.score_label)
        self.lives_label = TextObject(config.lives_offset,
                                      config.status_offset_y,
                                      lambda: f'LIVES: {self.lives}',
                                      config.text_color,
                                      config.font_name,
                                      config.font_size)
        self.objects.append(self.lives_label)

    def create_paddle(self):
        paddle = Paddle((config.screen_width - config.paddle_width) // 2,
                        config.screen_height - config.paddle_height * 2,
                        config.paddle_width,
                        config.paddle_height,
                        config.paddle_color,
                        config.paddle_speed)
        self.keydown_handlers[pygame.K_LEFT].append(paddle.handle)
        self.keydown_handlers[pygame.K_RIGHT].append(paddle.handle)
        self.keyup_handlers[pygame.K_LEFT].append(paddle.handle)
        self.keyup_handlers[pygame.K_RIGHT].append(paddle.handle)
        self.paddle = paddle
        self.objects.append(self.paddle)


    def create_bricks(self):
        w = config.brick_width
        h = config.brick_height
        brick_count = config.screen_width // (w + 1)
        offset_x = (config.screen_width - brick_count * (w + 1)) // 2
        bricks = []

        for row in range(config.row_count):
            for col in range(brick_count):
                effect = None
                brick_color = config.brick_color
                index = random.randint(0, 10)
                if index < len(special_effects):
                    x = list(special_effects.values())[index]
                    brick_color = x[0]
                    effect = x[1:]

                brick = Brick(offset_x + col * (w + 1),
                              config.offset_y + row * (h + 1),
                              w,
                              h,
                              brick_color,
                              effect)
                bricks.append(brick)
                self.objects.append(brick)
        self.bricks = bricks


    def update(self):
        if not self.is_game_running:
            return

        if self.start_level:
            self.start_level = False
            self.show_message('GET READY!', centralized=True)

        if not self.bricks:
            self.show_message('YOU WIN!!!', centralized=True)
            self.is_game_running = False
            self.game_over = True
            return

        # Reset special effect if needed
        if self.reset_effect:
            if datetime.now() - self.effect_start_time >= timedelta(seconds=config.effect_duration):
                self.reset_effect(self)
                self.reset_effect = None

        self.handle_ball_collisions()
        super().update()

        if self.game_over:
            self.show_message('GAME OVER!', centralized=True)
