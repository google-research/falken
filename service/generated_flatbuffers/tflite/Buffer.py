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

class Buffer(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsBuffer(cls, buf, offset):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = Buffer()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def BufferBufferHasIdentifier(cls, buf, offset, size_prefixed=False):
        return flatbuffers.util.BufferHasIdentifier(buf, offset, b"\x54\x46\x4C\x33", size_prefixed=size_prefixed)

    # Buffer
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # Buffer
    def Data(self, j):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            a = self._tab.Vector(o)
            return self._tab.Get(flatbuffers.number_types.Uint8Flags, a + flatbuffers.number_types.UOffsetTFlags.py_type(j * 1))
        return 0

    # Buffer
    def DataAsNumpy(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.GetVectorAsNumpy(flatbuffers.number_types.Uint8Flags, o)
        return 0

    # Buffer
    def DataLength(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # Buffer
    def DataIsNone(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        return o == 0

def BufferStart(builder): builder.StartObject(1)
def BufferAddData(builder, data): builder.PrependUOffsetTRelativeSlot(0, flatbuffers.number_types.UOffsetTFlags.py_type(data), 0)
def BufferStartDataVector(builder, numElems): return builder.StartVector(1, numElems, 1)
def BufferEnd(builder): return builder.EndObject()

try:
    from typing import List
except:
    pass

class BufferT(object):

    # BufferT
    def __init__(self):
        self.data = None  # type: List[int]

    @classmethod
    def InitFromBuf(cls, buf, pos):
        buffer = Buffer()
        buffer.Init(buf, pos)
        return cls.InitFromObj(buffer)

    @classmethod
    def InitFromObj(cls, buffer):
        x = BufferT()
        x._UnPack(buffer)
        return x

    # BufferT
    def _UnPack(self, buffer):
        if buffer is None:
            return
        if not buffer.DataIsNone():
            if np is None:
                self.data = []
                for i in range(buffer.DataLength()):
                    self.data.append(buffer.Data(i))
            else:
                self.data = buffer.DataAsNumpy()

    # BufferT
    def Pack(self, builder):
        if self.data is not None:
            if np is not None and type(self.data) is np.ndarray:
                data = builder.CreateNumpyVector(self.data)
            else:
                BufferStartDataVector(builder, len(self.data))
                for i in reversed(range(len(self.data))):
                    builder.PrependUint8(self.data[i])
                data = builder.EndVector(len(self.data))
        BufferStart(builder)
        if self.data is not None:
            BufferAddData(builder, data)
        buffer = BufferEnd(builder)
        return buffer
