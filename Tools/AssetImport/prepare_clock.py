"""Convert downloaded CC0 GLB into a centered 28 cm OBJ with material sections."""
from pathlib import Path
import json
import math
import struct

root = Path(__file__).resolve().parents[2]
folder = root / 'SourceAssets/Timer'
data = (folder / 'timer.glb').read_bytes()
json_size = struct.unpack_from('<I', data, 12)[0]
doc = json.loads(data[20:20 + json_size])
binary = data[28 + json_size:]

def accessor(index):
    item = doc['accessors'][index]
    view = doc['bufferViews'][item['bufferView']]
    count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[item['type']]
    fmt = {5123: 'H', 5125: 'I', 5126: 'f'}[item['componentType']]
    start = view.get('byteOffset', 0) + item.get('byteOffset', 0)
    stride = view.get('byteStride', struct.calcsize('<' + fmt * count))
    return [struct.unpack_from('<' + fmt * count, binary, start + i * stride) for i in range(item['count'])]

node = next(node for node in doc['nodes'] if 'mesh' in node)
assert len([n for n in doc['nodes'] if 'mesh' in n]) == 1
q = node.get('rotation', [0, 0, 0, 1])
scale = node.get('scale', [1, 1, 1])
translation = node.get('translation', [0, 0, 0])

def rotate(v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y*vz-z*vy), 2 * (z*vx-x*vz), 2 * (x*vy-y*vx)
    return [vx + w*tx + y*tz-z*ty, vy + w*ty + z*tx-x*tz, vz + w*tz + x*ty-y*tx]

vertices = []
primitives = []
for primitive in doc['meshes'][node['mesh']]['primitives']:
    assert primitive.get('mode', 4) == 4
    first = len(vertices)
    for vertex in accessor(primitive['attributes']['POSITION']):
        rotated = rotate([vertex[i] * scale[i] for i in range(3)])
        vertices.append([rotated[i] + translation[i] for i in range(3)])
    indices = [i[0] + first + 1 for i in accessor(primitive['indices'])]
    primitives.append((primitive['material'], indices))

mins = [min(v[i] for v in vertices) for i in range(3)]
maxs = [max(v[i] for v in vertices) for i in range(3)]
factor = 28.0 / max(maxs[i] - mins[i] for i in range(3))
center = [(mins[i] + maxs[i]) / 2 for i in range(3)]
lines = ['# Timer by scaranto, CC0; centered and scaled for Fruit_Example', 'mtllib clock.mtl', 'o Clock', 's off']
for vertex in vertices:
    p = [(vertex[i] - center[i]) * factor for i in range(3)]
    p = [p[0], -p[2], p[1]]  # OBJ importer uses Z-up coordinates in this project.
    lines.append('v ' + ' '.join(f'{value:.8f}' for value in p))
for material, indices in primitives:
    lines.append('usemtl Clock_' + str(material + 1).zfill(2))
    for i in range(0, len(indices), 3):
        lines.append('f ' + ' '.join(str(v) for v in indices[i:i+3]))
(folder / 'clock.obj').write_text('\n'.join(lines) + '\n', encoding='utf-8')
mtl = []
for i, material in enumerate(doc['materials']):
    color = material['pbrMetallicRoughness']['baseColorFactor']
    mtl.extend(['newmtl Clock_' + str(i + 1).zfill(2), 'Kd ' + ' '.join(str(c) for c in color[:3]), ''])
(folder / 'clock.mtl').write_text('\n'.join(mtl), encoding='utf-8')
(folder / 'materials.json').write_text(json.dumps(doc['materials'], indent=2), encoding='utf-8')
print('Prepared clock OBJ:', len(vertices), 'vertices;', len(lines), 'lines')
