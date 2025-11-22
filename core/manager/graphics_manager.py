import random
import time
from pathlib import Path
import pygame

# --- Constantes ---
RAYO_DURATION = 0.3
HIT_FLASH_DURATION = 0.3
MSG_DURATION = 0.8
LOOP_LENGTH = 3.75
HIT_WINDOW = 0.12
CLOUDIA_SPEED = 234
CLOUDIA_PAUSE = 0
FALL_SPEED = 400.0  # velocidad de caída
TICK_LENGTH = 0.1
ERR_MSG = 1.5

# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def _resolve_assets_path(override: str | None) -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / "assets" / "images"
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError("No se encontró 'assets/images' subiendo desde utils/.")


def _load_img(base: Path, name: str) -> pygame.Surface:
    full = base / name
    if not full.exists():
        raise FileNotFoundError(f"[Graphics] Falta asset: {full}")
    return pygame.image.load(str(full)).convert_alpha()


def _tint(surf: pygame.Surface, tint_color=(120, 180, 255), strength=80) -> pygame.Surface:
    copy = surf.copy()
    overlay = pygame.Surface(copy.get_size(), pygame.SRCALPHA)
    overlay.fill((*tint_color, strength))
    copy.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return copy


# ---------------------------------------------------------------------
# Entidades
# ---------------------------------------------------------------------
class Cloud(pygame.sprite.Sprite):
    def __init__(self, image: pygame.Surface, image_selected: pygame.Surface, pos: tuple[int, int]):
        super().__init__()
        self.image_base = image
        self.image_selected = image_selected
        self.image = self.image_base
        self.rect = self.image.get_rect(topleft=pos)

    def set_selected(self, selected: bool):
        self.image = self.image_selected if selected else self.image_base


class CloudIA:
    def __init__(self, image: pygame.Surface, screen_width: int):
        self.image_right = image
        self.image_left = pygame.transform.flip(image, True, False)
        self.image = self.image_left
        self.rect = self.image.get_rect(midtop=(screen_width // 2, 20))
        self.direction = 1
        self.x = float(self.rect.x)
        self.speed = CLOUDIA_SPEED
        self.pause_until = 0.0
        self.screen_width = screen_width
        self.oldtime = time.time()

    def update(self, dt):
        if time.time() < self.pause_until:
            return
        self.x += self.direction * self.speed * dt
        if self.x <= 20:
            self.direction = 1
            self.image = self.image_left
            self.pause_until = time.time() + CLOUDIA_PAUSE
            #calibrar tiempo
            #print("Cloudia ->", time.time()-self.oldtime)
            
            self.oldtime = time.time()
        elif self.x + self.rect.width >= self.screen_width - 20:
            self.direction = -1
            self.image = self.image_right
            self.pause_until = time.time() + CLOUDIA_PAUSE
            #calibrar tiempo
            #print("Cloudia <-", time.time()-self.oldtime)
            
            self.oldtime = time.time()
        self.rect.x = int(self.x)


class FallingEffect:
    """Rayos o notas que caen"""
    def __init__(self, image: pygame.Surface, x: int, y_start: int, duration: float = RAYO_DURATION, vy: float = FALL_SPEED):
        self.image = image
        self.x = x - image.get_width() // 2
        self.y = float(y_start)
        self.vy = vy
        self.until = time.time() + duration

    @property
    def alive(self) -> bool:
        return time.time() < self.until

    def update(self, dt):
        self.y += self.vy * dt

    def draw(self, surface: pygame.Surface):
        surface.blit(self.image, (int(self.x), int(self.y)))


# ---------------------------------------------------------------------
# GraphicsManager
# ---------------------------------------------------------------------
class GraphicsManager:
    """Gestiona todo el render y la lógica visual."""
    def __init__(self, assets_dir: str | None = None):
        self._assets_dir_override = assets_dir
        self.screen = None

        # Fondos
        self.bg_default = self.bg_level = self.bg_active = None
        self.current_bg = None

        # Sprites
        self.clouds_group = pygame.sprite.Group()
        self.cloud_list = []
        self.cloudia = None
        self.rayo_img = self.nota_img = None

        # Personajes
        self.main_idle = self.main_hit = None
        self.side_idle = self.side_hit = None
        self.main_rect = self.side1_rect = self.side2_rect = None
        self.main_hit_until = 0.0
        self.side_hit_until = 0.0
        # Matriz
        self.reference_matrix = {}
        self.inst_order = []
        self.inst_to_cloud_index = {}
        self.start_ts = None
        self.last_phase = 0.0

        # Nube seleccionada
        self.selected_cloud_index = 0

        # Rayos / notas
        self.effects = []

        # Progreso
        self.patterns_completed = [False, False, False]
        self.celebration_until = 0.0
        self.tick_until = 0.0
        
        self.curr_msg = ""
        self.end_status = False

    # --- carga ---
    def load_assets(self, screen: pygame.Surface):
        self.screen = screen
        self.base_f = _resolve_assets_path(self._assets_dir_override)
        base = self.base_f

        # Fondos
        self.bg_default = _load_img(base, "background15.png")
        self.bg_grey = _load_img(base, "background16.png")
        self.bg_hint = _load_img(base, "background17.png")
        self.hint = _load_img(base, "hint.png")
        self.bg_level = _load_img(base, "background2.png")
        self.bg_active = _load_img(base, "background1.png")
        self.bgs = [self.bg_default, self.bg_grey, self.bg_hint]
        self.current_bg = self.bgs[self.selected_cloud_index]

        # Sprites
        self.rayo_img = _load_img(base, "malo.png")
        self.nota_img = _load_img(base, "nota.png")

        self.anim_img = self.rayo_img

        self.cloud_imgs = [_load_img(base, f"cloud{i}a.png") for i in range(1, 4)]
        self.cloud_imgs_sel = [_tint(img, (120, 200, 255), 20) for img in self.cloud_imgs]
        self.width = screen.get_width()
        W, H = screen.get_width(), screen.get_height()
        self.cloudia = CloudIA(_load_img(base, "cloudia.png"), W)

        self.main_idle = _load_img(base, "tambor_g.png")
        self.main_hit = _load_img(base, "tambor_gs.png")
        self.side_idle = _load_img(base, "tambor_p_player.png")
        self.side_hit = _load_img(base, "tambor_p_player2.png")

        self.main_rect = self.main_idle.get_rect(midbottom=(W // 2, H - 220))
        self.side1_rect = self.side_idle.get_rect(midbottom=(W // 2 - 290, H - 110))
        self.side2_rect = self.side_idle.get_rect(midbottom=(W // 2 + 290, H - 110))
        self.hint_rect = self.hint.get_rect(midbottom=(W-350,H))

        self._place_clouds(self.cloud_imgs, self.cloud_imgs_sel, W)

        self.msg = _load_img(base, "msg.png")
        self.msg_rect = self.msg.get_rect(midbottom=(W // 2, 120 + (H // 2)))

    def set_end_status(self):
        self.end_status = True
    
    def tick(self):
        self.tick_until = time.time() + TICK_LENGTH

    def set_nube_buena(self, nube):
        self.cloud_imgs[nube] = _load_img(self.base_f, f"cloud{nube+1}.png")
    
    def update_bg(self):
        self.current_bg = self.bgs[self.selected_cloud_index]

    def _place_clouds(self, imgs, sel_imgs, W):
        rows_y = [60, 120, 180]
        rows_x = [120, 450, 850]
        used_x = []
        self.clouds_group.empty()
        self.cloud_list.clear()
        for idx, (img, img_sel) in enumerate(zip(imgs, sel_imgs)):
            #while True:
            #    x = random.randint(50, W - img.get_width() - 50)
            #    if all(abs(x - ox) > 180 for ox in used_x):
            #        break
            #used_x.append(x)
            x = rows_x[idx]
            y = rows_y[idx % len(rows_y)]
            c = Cloud(img, img_sel, (x, y))
            self.clouds_group.add(c)
            self.cloud_list.append(c)
        #OJO
        self._apply_selection(self.selected_cloud_index)

    # --- matriz ---
    def set_timeline_from_matrix(self, matrix):
        self.reference_matrix = {k: sorted(v) for k, v in matrix.items()}
        self.inst_order = sorted(self.reference_matrix.keys())
        self.inst_to_cloud_index = {inst: i for i, inst in enumerate(self.inst_order)}
        self.start_ts = time.time()
        self.last_phase = 0.0

    def _phase(self): return (time.time() - self.start_ts) % LOOP_LENGTH if self.start_ts else 0.0
    def _crossed(self, last, now, t):
        return (last < t <= now) if now >= last else (t > last or t <= now)

    # --- selección ---
    #def on_resonance(self, value_0_127):
    #    W = self.screen.get_width()
    #    target_x = int((value_0_127 / 127.0) * W)
    #    idx = min(range(len(self.cloud_list)), key=lambda i: abs(self.cloud_list[i].rect.centerx - target_x))
    #    self._apply_selection(idx)

    def _apply_selection(self, idx):
        self.selected_cloud_index = idx
        for i, c in enumerate(self.cloud_list):
            c.set_selected(i == idx)

    def next_nube(self):
        if self.selected_cloud_index < 3:
            self.selected_cloud_index = self.selected_cloud_index + 1

    def nerv_cloudia(self):
        self.cloudia.speed = self.cloudia.speed*2
    
    def set_msg(self, msg, error = False):
        self.curr_msg = msg
        if error:
            self.celebration_until = time.time() + ERR_MSG
        else:
            self.celebration_until = time.time() + MSG_DURATION
    
    

    # --- crush ---
    
    def on_crush(self):    
        self.main_hit_until = time.time() + HIT_FLASH_DURATION

        #if not self.inst_order or not self.start_ts:
        #    return
        #phase = self._phase()
        #inst = self.inst_order[self.selected_cloud_index]
        #events = self.reference_matrix.get(inst, [])
        #if not events: return
        #best_diff = min(min(abs(phase - t), abs((phase + LOOP_LENGTH) - t), abs((t + LOOP_LENGTH) - phase)) for t in events)
        #c = self.cloud_list[self.selected_cloud_index]
        #img = self.nota_img if best_diff <= HIT_WINDOW else self.rayo_img
        #self.effects.append(FallingEffect(img, c.rect.centerx, c.rect.bottom - 10))
        #if best_diff <= HIT_WINDOW:
        #    self.patterns_completed[self.selected_cloud_index] = True
        #    if self.has_completed_all_patterns():
        #        self.celebration_until = time.time() + 4.0
        #        self.set_active_background(True)

    def on_crush_midi(self):
        self.side_hit_until = time.time() + HIT_FLASH_DURATION

    # --- update ---
    def update(self, dt):
        if self.cloudia:
            self.cloudia.update(dt)
        if not self.reference_matrix: return
        now_phase = self._phase()
        
        #for i, inst in enumerate(self.inst_order):
        #    for t in self.reference_matrix[inst]:
        #        if self._crossed(self.last_phase, now_phase, t):
        #            c = self.cloud_list[i]
        #            self.effects.append(FallingEffect(self.rayo_img, c.rect.centerx, c.rect.bottom - 10))

        i = self.selected_cloud_index
        if i > 2:
            return
        
        inst = list(self.reference_matrix.keys())[i]
        for t in self.reference_matrix[inst]:
            if self._crossed(self.last_phase, now_phase, t):
                c = self.cloud_list[i]
                self.effects.append(FallingEffect(self.anim_img, c.rect.centerx, c.rect.bottom - 10))

        
        self.last_phase = now_phase
        self._update_effects(dt)

    def _update_effects(self, dt):
        H = self.screen.get_height()
        alive = []
        for e in self.effects:
            e.update(dt)
            if e.alive and e.y < H:
                alive.append(e)
        self.effects = alive

    # --- draw ---
    def draw(self):
        self.screen.blit(self.current_bg, (0, 0))
        self.screen.blit(self.bg_level, (0, 0))
        #if self.bg_level: self.screen.blit(self.bg_level, (0, 0))
        self.clouds_group.draw(self.screen)
        if self.cloudia: self.screen.blit(self.cloudia.image, self.cloudia.rect)
        img = self.main_hit if time.time() < self.main_hit_until else self.main_idle
        self.screen.blit(img, self.main_rect)

        imgs = self.side_hit if time.time() < self.side_hit_until else self.side_idle
        self.screen.blit(imgs, self.side1_rect)
        self.screen.blit(imgs, self.side2_rect)
        
        for e in self.effects:
            e.draw(self.screen)

        if all(self.patterns_completed) and self.end_status == False:
            self.screen.blit(self.hint, (0,0))
        # Mensaje de celebración
        if time.time() < self.celebration_until or self.end_status:
            self.screen.blit(self.msg, self.msg_rect)
            #overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            #overlay.fill((64, 36, 15, 80))
            #self.screen.blit(overlay, (0, 0))
            font = pygame.font.Font(None, 72)
            text = font.render(self.curr_msg, True, (64, 36, 15))
            rect = text.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2))
            self.screen.blit(text, rect)
        
        if time.time() < self.tick_until:
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 70))
            self.screen.blit(overlay, (0, 0))


    # --- extra ---
    def has_completed_all_patterns(self) -> bool:
        return all(self.patterns_completed)

    def set_active_background(self, active: bool):
        self.current_bg = self.bg_active if active else self.bg_default
