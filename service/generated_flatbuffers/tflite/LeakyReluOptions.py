# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# automatically generated by the FlatBuffers compiler, do not modify

# namespace: tflite

import flatbuffers
from flatbuffers.compat import import_numpy
np = import_numpy()

class LeakyReluOptions(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsLeakyReluOptions(cls, buf, offset):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = LeakyReluOptions()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def LeakyReluOptionsBufferHasIdentifier(cls, buf, offset, size_prefixed=False):
        return flatbuffers.util.BufferHasIdentifier(buf, offset, b"\x54\x46\x4C\x33", size_prefixed=size_prefixed)

    # LeakyReluOptions
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # LeakyReluOptions
    def Alpha(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Float32Flags, o + self._tab.Pos)
        return 0.0

def LeakyReluOptionsStart(builder): builder.StartObject(1)
def LeakyReluOptionsAddAlpha(builder, alpha): builder.PrependFloat32Slot(0, alpha, 0.0)
def LeakyReluOptionsEnd(builder): return builder.EndObject()


class LeakyReluOptionsT(object):

    # LeakyReluOptionsT
    def __init__(self):
        self.alpha = 0.0  # type: float

    @classmethod
    def InitFromBuf(cls, buf, pos):
        leakyReluOptions = LeakyReluOptions()
        leakyReluOptions.Init(buf, pos)
        return cls.InitFromObj(leakyReluOptions)

    @classmethod
    def InitFromObj(cls, leakyReluOptions):
        x = LeakyReluOptionsT()
        x._UnPack(leakyReluOptions)
        return x

    # LeakyReluOptionsT
    def _UnPack(self, leakyReluOptions):
        if leakyReluOptions is None:
            return
        self.alpha = leakyReluOptions.Alpha()

    # LeakyReluOptionsT
    def Pack(self, builder):
        LeakyReluOptionsStart(builder)
        LeakyReluOptionsAddAlpha(builder, self.alpha)
        leakyReluOptions = LeakyReluOptionsEnd(builder)
        return leakyReluOptions
