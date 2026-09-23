"""Grid 12 colunas; coordenadas de projeto em px de referência, não percentuais soltos."""
from dataclasses import dataclass
from math import ceil, floor, isfinite


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self): return self.x + self.width

    @property
    def bottom(self): return self.y + self.height

    def contains(self, other: 'Box', tolerance: float = 0.01) -> bool:
        return (other.x >= self.x-tolerance and other.y >= self.y-tolerance
                and other.right <= self.right+tolerance and other.bottom <= self.bottom+tolerance)

    def pixels(self):
        return tuple(round(v) for v in (self.x, self.y, self.right, self.bottom))


class Grid:
    """1080x1920: safe=(72,140,936,1530), gutter=24, column=56.

    1:1 é remontado em artboard próprio. Top140/bottom250 são mínimos;
    o conteúdo é alinhado para dentro ao baseline8 (144 e1664).
    """
    columns = 12

    def __init__(self, width: int, height: int):
        if isinstance(width, bool) or isinstance(height, bool) or min(width, height) < 240:
            raise ValueError('Canvas deve ter ao menos 240 px; previews menores são derivados.')
        self.width, self.height = int(width), int(height)
        self.scale = min(width, height) / 1080
        self.unit = 8 * self.scale
        self.gutter = 24 * self.scale
        side = 72 * self.scale
        if height / width >= 1.6:
            top, bottom = 140 * self.scale, 250 * self.scale
        elif height > width:
            top, bottom = 80 * self.scale, 104 * self.scale
        else:
            top = bottom = 64 * self.scale
        self.safe = Box(side, top, width-2*side, height-top-bottom)
        y0, y1 = self.snap(top, 'up'), self.snap(height-bottom, 'down')
        self.editorial = Box(side, y0, width-2*side, y1-y0)
        self.column = (self.editorial.width-11*self.gutter)/12
        size = min(self.editorial.width, self.editorial.height)
        size = self.snap(size, 'down')
        self.kernel = Box((width-size)/2, self.snap((height-size)/2, 'down'), size, size)
        if not self.safe.contains(self.kernel):
            self.kernel = Box((width-size)/2, self.editorial.y, size, size)

    def snap(self, value: float, direction='nearest') -> float:
        if not isfinite(value): raise ValueError('Coordenada não finita.')
        op = {'up': ceil, 'down': floor, 'nearest': round}[direction]
        return op(value/self.unit)*self.unit

    def span(self, start: int, count: int, y: float, height: float) -> Box:
        if not 0 <= start < 12 or not 1 <= count <= 12-start:
            raise ValueError('Colunas fora do grid.')
        result = Box(self.editorial.x+start*(self.column+self.gutter), y,
                     count*self.column+(count-1)*self.gutter, height)
        if not self.safe.contains(result): raise ValueError('Caixa invade safe area.')
        return result

    def validate(self, boxes: dict[str, Box]) -> list[str]:
        return [name for name, box in boxes.items() if not self.safe.contains(box)]
