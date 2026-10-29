"""swmmout.py - minimal reader for EPA SWMM 5 binary output (.out) files.

Reads the header, object IDs, the reporting-period dates and any requested time series.
Written by Claude (Anthropic); see AI-USE.md.
"""
import struct

MAGIC = 516114522
SUBCATCH_VARS0, NODE_VARS0, LINK_VARS0, SYS_VARS = 8, 6, 5, 15   # before pollutants


class SwmmOut:
    def __init__(self, path):
        self.b = open(path, 'rb').read()
        b = self.b
        if len(b) < 7 * 4 * 2:
            raise ValueError('too short')
        tail = struct.unpack_from('<6i', b, len(b) - 24)
        self.id_pos, self.input_pos, self.output_pos, self.nperiods, self.error_code, magic2 = tail
        head = struct.unpack_from('<7i', b, 0)
        if head[0] != MAGIC or magic2 != MAGIC:
            raise ValueError('not a SWMM5 output file')
        self.version, self.flow_units = head[1], head[2]
        self.nsub, self.nnode, self.nlink, self.npoll = head[3:7]
        p = self.id_pos
        names = []
        for _ in range(self.nsub + self.nnode + self.nlink + self.npoll):
            n = struct.unpack_from('<i', b, p)[0]
            p += 4
            names.append(b[p:p + n].decode('latin-1'))
            p += n
        self.subcatch = names[:self.nsub]
        self.nodes = names[self.nsub:self.nsub + self.nnode]
        self.links = names[self.nsub + self.nnode:self.nsub + self.nnode + self.nlink]
        self.polluts = names[self.nsub + self.nnode + self.nlink:]
        # reporting variables
        p = self.input_pos
        p += 4 * (2 + self.nsub)                 # subcatch: count, 1 property code, area of each
        p += 4 * (4 + 3 * self.nnode)            # node: count, 3 codes, 3 values each
        p += 4 * (6 + 5 * self.nlink)            # link: count, 5 codes, 5 values each
        nsv = struct.unpack_from('<i', b, p)[0]; p += 4 * (1 + nsv)
        nnv = struct.unpack_from('<i', b, p)[0]; p += 4 * (1 + nnv)
        nlv = struct.unpack_from('<i', b, p)[0]; p += 4 * (1 + nlv)
        nyv = struct.unpack_from('<i', b, p)[0]; p += 4 * (1 + nyv)
        self.nsv, self.nnv, self.nlv, self.nyv = nsv, nnv, nlv, nyv
        self.start_date = struct.unpack_from('<d', b, p)[0]
        self.report_step = struct.unpack_from('<i', b, p + 8)[0]
        self.bytes_per_period = 8 + 4 * (self.nsub * nsv + self.nnode * nnv + self.nlink * nlv + nyv)
        if p + 12 != self.output_pos:
            raise ValueError('layout check failed: results expected at %d, header says %d' % (p + 12, self.output_pos))

    def period_offset(self, k):
        return self.output_pos + k * self.bytes_per_period

    def dates(self):
        return [struct.unpack_from('<d', self.b, self.period_offset(k))[0] for k in range(self.nperiods)]

    def series(self, kind, index, var):
        """kind 'sub'|'node'|'link'|'sys'; var = variable number within that kind"""
        base = 8
        if kind == 'sub':
            off = base + 4 * (index * self.nsv + var)
        elif kind == 'node':
            off = base + 4 * (self.nsub * self.nsv + index * self.nnv + var)
        elif kind == 'link':
            off = base + 4 * (self.nsub * self.nsv + self.nnode * self.nnv + index * self.nlv + var)
        else:
            off = base + 4 * (self.nsub * self.nsv + self.nnode * self.nnv + self.nlink * self.nlv + var)
        return [struct.unpack_from('<f', self.b, self.period_offset(k) + off)[0] for k in range(self.nperiods)]


NODE_VAR_NAMES = ['depth', 'head', 'volume', 'lateral inflow', 'total inflow', 'flooding']
LINK_VAR_NAMES = ['flow', 'depth', 'velocity', 'volume', 'capacity']
SYS_VAR_NAMES = ['air temperature', 'rainfall', 'snow depth', 'infiltration', 'runoff', 'dry weather inflow',
                 'groundwater inflow', 'RDII inflow', 'external inflow', 'total lateral inflow', 'flooding',
                 'outfall outflow', 'storage volume', 'evaporation', 'PET']
