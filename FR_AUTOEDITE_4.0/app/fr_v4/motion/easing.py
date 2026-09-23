from math import cos, pi


def ease(value: float, curve='easeOutQuint') -> float:
    t=max(0.,min(1.,float(value)))
    if curve=='easeOutQuint': return 1-(1-t)**5
    if curve=='easeOutCubic': return 1-(1-t)**3
    if curve=='easeInOutCubic': return 4*t**3 if t<.5 else 1-(-2*t+2)**3/2
    if curve=='easeInOutSine': return -(cos(pi*t)-1)/2
    raise ValueError('Curva não autorizada.')


def ffmpeg_expression(variable='t', curve='easeInOutSine') -> str:
    if variable not in {'t','T','on'}: raise ValueError('Variável inválida.')
    t=f'clip({variable},0,1)'
    return {'easeOutQuint':f'1-pow(1-{t},5)',
            'easeOutCubic':f'1-pow(1-{t},3)',
            'easeInOutSine':f'(1-cos(PI*{t}))/2',
            'easeInOutCubic':f'if(lt({t},0.5),4*pow({t},3),1-pow(-2*{t}+2,3)/2)'}[curve]
