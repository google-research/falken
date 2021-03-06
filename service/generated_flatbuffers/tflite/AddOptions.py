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

class AddOptions(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsAddOptions(cls, buf, offset):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = AddOptions()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def AddOptionsBufferHasIdentifier(cls, buf, offset, size_prefixed=False):
        return flatbuffers.util.BufferHasIdentifier(buf, offset, b"\x54\x46\x4C\x33", size_prefixed=size_prefixed)

    # AddOptions
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # AddOptions
    def FusedActivationFunction(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(flatbuffers.number_types.Int8Flags, o + self._tab.Pos)
        return 0

    # AddOptions
    def PotScaleInt16(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return bool(self._tab.Get(flatbuffers.number_types.BoolFlags, o + self._tab.Pos))
        return True

def AddOptionsStart(builder): builder.StartObject(2)
def AddOptionsAddFusedActivationFunction(builder, fusedActivationFunction): builder.PrependInt8Slot(0, fusedActivationFunction, 0)
def AddOptionsAddPotScaleInt16(builder, potScaleInt16): builder.PrependBoolSlot(1, potScaleInt16, 1)
def AddOptionsEnd(builder): return builder.EndObject()


class AddOptionsT(object):

    # AddOptionsT
    def __init__(self):
        self.fusedActivationFunction = 0  # type: int
        self.potScaleInt16 = True  # type: bool

    @classmethod
    def InitFromBuf(cls, buf, pos):
        addOptions = AddOptions()
        addOptions.Init(buf, pos)
        return cls.InitFromObj(addOptions)

    @classmethod
    def InitFromObj(cls, addOptions):
        x = AddOptionsT()
        x._UnPack(addOptions)
        return x

    # AddOptionsT
    def _UnPack(self, addOptions):
        if addOptions is None:
            return
        self.fusedActivationFunction = addOptions.FusedActivationFunction()
        self.potScaleInt16 = addOptions.PotScaleInt16()

    # AddOptionsT
    def Pack(self, builder):
        AddOptionsStart(builder)
        AddOptionsAddFusedActivationFunction(builder, self.fusedActivationFunction)
        AddOptionsAddPotScaleInt16(builder, self.potScaleInt16)
        addOptions = AddOptionsEnd(builder)
        return addOptions
