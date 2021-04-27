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

class FloorDivOptions(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsFloorDivOptions(cls, buf, offset):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = FloorDivOptions()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def FloorDivOptionsBufferHasIdentifier(cls, buf, offset, size_prefixed=False):
        return flatbuffers.util.BufferHasIdentifier(buf, offset, b"\x54\x46\x4C\x33", size_prefixed=size_prefixed)

    # FloorDivOptions
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

def FloorDivOptionsStart(builder): builder.StartObject(0)
def FloorDivOptionsEnd(builder): return builder.EndObject()


class FloorDivOptionsT(object):

    # FloorDivOptionsT
    def __init__(self):
        pass

    @classmethod
    def InitFromBuf(cls, buf, pos):
        floorDivOptions = FloorDivOptions()
        floorDivOptions.Init(buf, pos)
        return cls.InitFromObj(floorDivOptions)

    @classmethod
    def InitFromObj(cls, floorDivOptions):
        x = FloorDivOptionsT()
        x._UnPack(floorDivOptions)
        return x

    # FloorDivOptionsT
    def _UnPack(self, floorDivOptions):
        if floorDivOptions is None:
            return

    # FloorDivOptionsT
    def Pack(self, builder):
        FloorDivOptionsStart(builder)
        floorDivOptions = FloorDivOptionsEnd(builder)
        return floorDivOptions