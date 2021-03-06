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

class ZerosLikeOptions(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsZerosLikeOptions(cls, buf, offset):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = ZerosLikeOptions()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def ZerosLikeOptionsBufferHasIdentifier(cls, buf, offset, size_prefixed=False):
        return flatbuffers.util.BufferHasIdentifier(buf, offset, b"\x54\x46\x4C\x33", size_prefixed=size_prefixed)

    # ZerosLikeOptions
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

def ZerosLikeOptionsStart(builder): builder.StartObject(0)
def ZerosLikeOptionsEnd(builder): return builder.EndObject()


class ZerosLikeOptionsT(object):

    # ZerosLikeOptionsT
    def __init__(self):
        pass

    @classmethod
    def InitFromBuf(cls, buf, pos):
        zerosLikeOptions = ZerosLikeOptions()
        zerosLikeOptions.Init(buf, pos)
        return cls.InitFromObj(zerosLikeOptions)

    @classmethod
    def InitFromObj(cls, zerosLikeOptions):
        x = ZerosLikeOptionsT()
        x._UnPack(zerosLikeOptions)
        return x

    # ZerosLikeOptionsT
    def _UnPack(self, zerosLikeOptions):
        if zerosLikeOptions is None:
            return

    # ZerosLikeOptionsT
    def Pack(self, builder):
        ZerosLikeOptionsStart(builder)
        zerosLikeOptions = ZerosLikeOptionsEnd(builder)
        return zerosLikeOptions
