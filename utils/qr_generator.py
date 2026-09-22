"""Pure Python QR Code Generator that outputs clean SVG strings.
Supports Byte mode encoding (URL, text) and standard QR Code generation (versions 1-10).
"""
import io
import math


def generate_qr_svg(data: str, box_size: int = 10, border: int = 4) -> str:
    """Generate a clean SVG string representing a scannable QR Code for `data`."""
    matrix = _make_qr_matrix(data)
    size = len(matrix)
    total_size = (size + border * 2) * box_size
    
    path_d = []
    for r in range(size):
        for c in range(size):
            if matrix[r][c]:
                x = (c + border) * box_size
                y = (r + border) * box_size
                path_d.append(f"M{x},{y}h{box_size}v{box_size}h-{box_size}z")
                
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_size} {total_size}" '
        f'width="{total_size}" height="{total_size}">\n'
        f'  <rect width="100%" height="100%" fill="#ffffff"/>\n'
        f'  <path d="{" ".join(path_d)}" fill="#0f172a"/>\n'
        f'</svg>'
    )
    return svg


# ---------------------------------------------------------------------- QR Algorithm Engine

def _make_qr_matrix(data: str):
    data_bytes = data.encode('utf-8')
    # Pick smallest QR version (1 to 10 with M error correction)
    version = _pick_version(len(data_bytes))
    size = version * 4 + 17
    matrix = [[None] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    def set_module(r, c, val, is_reserved=True):
        matrix[r][c] = 1 if val else 0
        if is_reserved:
            reserved[r][c] = True

    # 1. Finder patterns
    def draw_finder(r0, c0):
        for r in range(-1, 8):
            for c in range(-1, 8):
                r_idx, c_idx = r0 + r, c0 + c
                if 0 <= r_idx < size and 0 <= c_idx < size:
                    is_black = (0 <= r <= 6 and c in (0, 6)) or (0 <= c <= 6 and r in (0, 6)) or (2 <= r <= 4 and 2 <= c <= 4)
                    set_module(r_idx, c_idx, is_black)

    draw_finder(0, 0)
    draw_finder(0, size - 7)
    draw_finder(size - 7, 0)

    # 2. Alignment patterns for Version >= 2
    align_pos = _ALIGNMENT_POS.get(version, [])
    for r in align_pos:
        for c in align_pos:
            if matrix[r][c] is not None:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    is_black = max(abs(dr), abs(dc)) != 1
                    set_module(r + dr, c + dc, is_black)

    # 3. Timing patterns
    for i in range(8, size - 8):
        if matrix[6][i] is None:
            set_module(6, i, i % 2 == 0)
        if matrix[i][6] is None:
            set_module(i, 6, i % 2 == 0)

    # 4. Dark module
    set_module(4 * version + 9, 8, True)

    # Reserve format info areas
    for i in range(9):
        if matrix[8][i] is None:
            matrix[8][i] = 0
            reserved[8][i] = True
        if matrix[i][8] is None:
            matrix[i][8] = 0
            reserved[i][8] = True
    for i in range(8):
        if matrix[8][size - 1 - i] is None:
            matrix[8][size - 1 - i] = 0
            reserved[8][size - 1 - i] = True
        if matrix[size - 1 - i][8] is None:
            matrix[size - 1 - i][8] = 0
            reserved[size - 1 - i][8] = True

    # 5. Build codewords (Byte mode, Error Correction Level M)
    codewords = _build_codewords(data_bytes, version)

    # 6. Place data bits
    bits = []
    for cw in codewords:
        for b in range(7, -1, -1):
            bits.append((cw >> b) & 1)

    bit_idx = 0
    num_bits = len(bits)
    direction = -1
    col = size - 1
    row = size - 1

    while col > 0:
        if col == 6:
            col -= 1
        for _ in range(size):
            r = row
            for c in (col, col - 1):
                if not reserved[r][c]:
                    bval = bits[bit_idx] if bit_idx < num_bits else 0
                    matrix[r][c] = bval
                    bit_idx += 1
            row += direction
        direction = -direction
        row += direction
        col -= 2

    # 7. Apply pattern mask 0 ( (r+c)%2 == 0 ) & Write format info
    mask_pattern = 0
    for r in range(size):
        for c in range(size):
            if not reserved[r][c]:
                if (r + c) % 2 == 0:
                    matrix[r][c] ^= 1

    # Format info for EC Level M (00) and Mask 0 (000) -> 00000 -> BCH (15,5) code
    format_bits = 0b101010000010010  # Pre-computed BCH for (M, mask=0) XORed with 101010000010010
    
    # Place format bits
    fmt_pos1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8), (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    fmt_pos2 = [(size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8), (size - 5, 8), (size - 6, 8), (size - 7, 8),
                (8, size - 8), (8, size - 7), (8, size - 6), (8, size - 5), (8, size - 4), (8, size - 3), (8, size - 2), (8, size - 1)]

    for idx, (r, c) in enumerate(fmt_pos1):
        matrix[r][c] = (format_bits >> idx) & 1
    for idx, (r, c) in enumerate(fmt_pos2):
        matrix[r][c] = (format_bits >> idx) & 1

    return matrix


_ALIGNMENT_POS = {
    2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
    7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]
}

_VERSION_CAPACITIES_M = {
    1: (16, 10, 16), 2: (28, 16, 28), 3: (44, 26, 44), 4: (64, 36, 64),
    5: (86, 48, 86), 6: (108, 64, 108), 7: (124, 72, 124), 8: (154, 88, 154),
    9: (182, 110, 182), 10: (216, 130, 216)
}


def _pick_version(data_len: int) -> int:
    for v in range(1, 11):
        total_cw, ec_cw, data_cw = _VERSION_CAPACITIES_M[v]
        if data_len + 3 <= data_cw:
            return v
    return 10


def _build_codewords(data_bytes: bytes, version: int):
    total_cw, ec_cw, data_cw = _VERSION_CAPACITIES_M[version]
    # Bit stream: 4 bits mode indicator (0100 for Byte mode) + 8 bits char count + data + 4 bits terminator
    bits = []
    # Byte mode = 0100
    bits.extend([0, 1, 0, 0])
    count = len(data_bytes)
    for b in range(7, -1, -1):
        bits.append((count >> b) & 1)
    for byte in data_bytes:
        for b in range(7, -1, -1):
            bits.append((byte >> b) & 1)
    # Terminator
    bits.extend([0, 0, 0, 0])
    # Align to byte
    while len(bits) % 8 != 0:
        bits.append(0)

    codewords = []
    for i in range(0, len(bits), 8):
        cw = 0
        for b in range(8):
            cw = (cw << 1) | bits[i + b]
        codewords.append(cw)

    # Pad codewords if under capacity
    pad_bytes = [236, 17]
    pad_idx = 0
    while len(codewords) < data_cw:
        codewords.append(pad_bytes[pad_idx])
        pad_idx = (pad_idx + 1) % 2

    codewords = codewords[:data_cw]

    # Calculate Reed-Solomon Error Correction Codewords
    ec_bytes = _rs_encode(codewords, ec_cw)
    return codewords + ec_bytes


def _rs_encode(data, n_ec):
    gen = _rs_generator_poly(n_ec)
    res = list(data) + [0] * n_ec
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(len(gen)):
                res[i + j] ^= _gf_mul(gen[j], coef)
    return res[len(data):]


# Galois Field GF(256) arithmetic with primitive polynomial 0x11d
_GF_EXP = [1] * 512
_GF_LOG = [0] * 256
_x = 1
for _i in range(1, 255):
    _x <<= 1
    if _x & 256:
        _x ^= 0x11d
    _GF_EXP[_i] = _x
    _GF_LOG[_x] = _i
for _i in range(255, 512):
    _GF_EXP[_i] = _GF_EXP[_i - 255]


def _gf_mul(x, y):
    if x == 0 or y == 0:
        return 0
    return _GF_EXP[_GF_LOG[x] + _GF_LOG[y]]


def _rs_generator_poly(n):
    g = [1]
    for i in range(n):
        g = _poly_mul(g, [1, _GF_EXP[i]])
    return g


def _poly_mul(p1, p2):
    res = [0] * (len(p1) + len(p2) - 1)
    for i, c1 in enumerate(p1):
        for j, c2 in enumerate(p2):
            res[i + j] ^= _gf_mul(c1, c2)
    return res
