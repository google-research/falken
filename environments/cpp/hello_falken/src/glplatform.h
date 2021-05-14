// Copyright 2014 Google Inc. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// clang-format off

// OpenGL platform definitions

#ifndef FPLBASE_GLPLATFORM_H
#define FPLBASE_GLPLATFORM_H

#ifdef __APPLE__
#  include "TargetConditionals.h"
#  if TARGET_OS_IPHONE || TARGET_IPHONE_SIMULATOR
#    define PLATFORM_MOBILE
#    define FPLBASE_GLES
#    include <OpenGLES/ES3/gl.h>
#    include <OpenGLES/ES3/glext.h>
#  else  // TARGET_OS_IPHONE || TARGET_IPHONE_SIMULATOR
#    define PLATFORM_OSX
#    include <OpenGL/gl3.h>
#    include <OpenGL/gl3ext.h>
#  endif  // TARGET_OS_IPHONE || TARGET_IPHONE_SIMULATOR

#else  // !defined(__APPLE__)
#  ifdef __ANDROID__
#    define PLATFORM_MOBILE
#    define FPLBASE_GLES
#    include <EGL/egl.h>
#    include <android/api-level.h>
#    ifndef GL_TEXTURE_EXTERNAL_OES
#      define GL_TEXTURE_EXTERNAL_OES 0x8D65
#    endif
#    if __ANDROID_API__ >= 18
#      include <GLES3/gl3.h>
#    else  // __ANDROID_API__ < 18
#      include <GLES2/gl2.h>
#      include "gl3stub.h"
#    endif  // __ANDROID_API__ < 18
#  elif defined(__EMSCRIPTEN__) // !defined(__ANDROID__)
#    define PLATFORM_MOBILE
#    define FPLBASE_GLES
#    include <EGL/egl.h>
#    include <GLES3/gl3.h>
#  else  // !defined(__ANDROID__) && !defined(__EMSCRIPTEN__), so WIN32 & Linux
#    ifdef _WIN32
#      define VC_EXTRALEAN
#      ifndef WIN32_LEAN_AND_MEAN
#        define WIN32_LEAN_AND_MEAN
#      endif  // !defined(WIN32_LEAN_AND_MEAN)
#      ifndef NOMINMAX
#        define NOMINMAX
#      endif  // !defined(NOMINMAX)
#      include <windows.h>
// Windows GDI defines ERROR.  Prevent it leaking from this header.
#      ifdef ERROR
#        undef ERROR
#      endif
#    endif  // !defined(_WIN32)

#    include <GL/gl.h>
#    include <GL/glext.h>
#    if !defined(GL_GLEXT_PROTOTYPES)
#      ifdef _WIN32
#        define GLBASEEXTS                                                     \
         GLEXT(PFNGLACTIVETEXTUREARBPROC, glActiveTexture, true)               \
         GLEXT(PFNGLCOMPRESSEDTEXIMAGE2DPROC, glCompressedTexImage2D, true)    \
         GLEXT(PFNGLBINDSAMPLERPROC, glBindSampler, true)
#      else   // !defined(_WIN32)
#        define GLBASEEXTS
#      endif  // !defined(_WIN32)
#      define GLEXTS                                                           \
       GLEXT(PFNGLGETSTRINGIPROC, glGetStringi, true)                          \
       GLEXT(PFNGLGENFRAMEBUFFERSPROC, glGenFramebuffers, true)                \
       GLEXT(PFNGLBINDFRAMEBUFFEREXTPROC, glBindFramebuffer, true)             \
       GLEXT(PFNGLGENRENDERBUFFERSEXTPROC, glGenRenderbuffers, true)           \
       GLEXT(PFNGLBINDRENDERBUFFEREXTPROC, glBindRenderbuffer, true)           \
       GLEXT(PFNGLRENDERBUFFERSTORAGEEXTPROC, glRenderbufferStorage, true)     \
       GLEXT(PFNGLFRAMEBUFFERRENDERBUFFEREXTPROC, glFramebufferRenderbuffer,   \
             true)                                                             \
       GLEXT(PFNGLFRAMEBUFFERTEXTURE2DPROC, glFramebufferTexture2D, true)      \
       GLEXT(PFNGLDRAWBUFFERSPROC, glDrawBuffers, true)                        \
       GLEXT(PFNGLCHECKFRAMEBUFFERSTATUSEXTPROC, glCheckFramebufferStatus,     \
             true)                                                             \
       GLEXT(PFNGLDELETERENDERBUFFERSEXTPROC, glDeleteRenderbuffers, true)     \
       GLEXT(PFNGLDELETEFRAMEBUFFERSEXTPROC, glDeleteFramebuffers, true)       \
       GLEXT(PFNGLGENBUFFERSARBPROC, glGenBuffers, true)                       \
       GLEXT(PFNGLBINDBUFFERARBPROC, glBindBuffer, true)                       \
       GLEXT(PFNGLMAPBUFFERARBPROC, glMapBuffer, true)                         \
       GLEXT(PFNGLUNMAPBUFFERARBPROC, glUnmapBuffer, true)                     \
       GLEXT(PFNGLBUFFERDATAARBPROC, glBufferData, true)                       \
       GLEXT(PFNGLBUFFERSUBDATAARBPROC, glBufferSubData, true)                 \
       GLEXT(PFNGLDELETEBUFFERSARBPROC, glDeleteBuffers, true)                 \
       GLEXT(PFNGLGETBUFFERSUBDATAARBPROC, glGetBufferSubData, true)           \
       GLEXT(PFNGLVERTEXATTRIBPOINTERARBPROC, glVertexAttribPointer, true)     \
       GLEXT(PFNGLENABLEVERTEXATTRIBARRAYARBPROC, glEnableVertexAttribArray,   \
             true)                                                             \
       GLEXT(PFNGLDISABLEVERTEXATTRIBARRAYARBPROC, glDisableVertexAttribArray, \
             true)                                                             \
       GLEXT(PFNGLCREATEPROGRAMPROC, glCreateProgram, true)                    \
       GLEXT(PFNGLDELETEPROGRAMPROC, glDeleteProgram, true)                    \
       GLEXT(PFNGLDELETESHADERPROC, glDeleteShader, true)                      \
       GLEXT(PFNGLUSEPROGRAMPROC, glUseProgram, true)                          \
       GLEXT(PFNGLCREATESHADERPROC, glCreateShader, true)                      \
       GLEXT(PFNGLSHADERSOURCEPROC, glShaderSource, true)                      \
       GLEXT(PFNGLSTENCILFUNCSEPARATEPROC, glStencilFuncSeparate, true)        \
       GLEXT(PFNGLSTENCILOPSEPARATEPROC, glStencilOpSeparate, true)            \
       GLEXT(PFNGLCOMPILESHADERPROC, glCompileShader, true)                    \
       GLEXT(PFNGLGETPROGRAMIVARBPROC, glGetProgramiv, true)                   \
       GLEXT(PFNGLGETSHADERIVPROC, glGetShaderiv, true)                        \
       GLEXT(PFNGLGETPROGRAMINFOLOGPROC, glGetProgramInfoLog, true)            \
       GLEXT(PFNGLGETSHADERINFOLOGPROC, glGetShaderInfoLog, true)              \
       GLEXT(PFNGLATTACHSHADERPROC, glAttachShader, true)                      \
       GLEXT(PFNGLLINKPROGRAMARBPROC, glLinkProgram, true)                     \
       GLEXT(PFNGLGETUNIFORMLOCATIONARBPROC, glGetUniformLocation, true)       \
       GLEXT(PFNGLUNIFORM1FARBPROC, glUniform1f, true)                         \
       GLEXT(PFNGLUNIFORM2FARBPROC, glUniform2f, true)                         \
       GLEXT(PFNGLUNIFORM3FARBPROC, glUniform3f, true)                         \
       GLEXT(PFNGLUNIFORM4FARBPROC, glUniform4f, true)                         \
       GLEXT(PFNGLUNIFORM1FVARBPROC, glUniform1fv, true)                       \
       GLEXT(PFNGLUNIFORM2FVARBPROC, glUniform2fv, true)                       \
       GLEXT(PFNGLUNIFORM3FVARBPROC, glUniform3fv, true)                       \
       GLEXT(PFNGLUNIFORM4FVARBPROC, glUniform4fv, true)                       \
       GLEXT(PFNGLUNIFORM1IARBPROC, glUniform1i, true)                         \
       GLEXT(PFNGLUNIFORM1IVARBPROC, glUniform1iv, true)                       \
       GLEXT(PFNGLUNIFORM2IARBPROC, glUniform2i, true)                         \
       GLEXT(PFNGLUNIFORM2IVARBPROC, glUniform2iv, true)                       \
       GLEXT(PFNGLUNIFORM3IARBPROC, glUniform3i, true)                         \
       GLEXT(PFNGLUNIFORM3IVARBPROC, glUniform3iv, true)                       \
       GLEXT(PFNGLUNIFORM4IARBPROC, glUniform4i, true)                         \
       GLEXT(PFNGLUNIFORM4IVARBPROC, glUniform4iv, true)                       \
       GLEXT(PFNGLUNIFORMMATRIX2FVARBPROC, glUniformMatrix2fv, true)           \
       GLEXT(PFNGLUNIFORMMATRIX3FVARBPROC, glUniformMatrix3fv, true)           \
       GLEXT(PFNGLUNIFORMMATRIX4FVARBPROC, glUniformMatrix4fv, true)           \
       GLEXT(PFNGLUNIFORMMATRIX4FVARBPROC /*type*/, glUniformMatrix3x4fv, true)\
       GLEXT(PFNGLBINDATTRIBLOCATIONARBPROC, glBindAttribLocation, true)       \
       GLEXT(PFNGLGETACTIVEUNIFORMARBPROC, glGetActiveUniform, true)           \
       GLEXT(PFNGLGENERATEMIPMAPEXTPROC, glGenerateMipmap, true)               \
       GLEXT(PFNGLGETATTRIBLOCATIONPROC, glGetAttribLocation, true)            \
       GLEXT(PFNGLDRAWELEMENTSINSTANCEDPROC, glDrawElementsInstanced, true)    \
       GLEXT(PFNGLGENVERTEXARRAYSPROC, glGenVertexArrays, true)                \
       GLEXT(PFNGLDELETEVERTEXARRAYSPROC, glDeleteVertexArrays, true)          \
       GLEXT(PFNGLBINDVERTEXARRAYPROC, glBindVertexArray, true)                \
       GLEXT(PFNGLFRAMEBUFFERTEXTUREMULTIVIEWOVRPROC,                          \
             glFramebufferTextureMultiviewOVR, false)                          \
       GLEXT(PFNGLGETUNIFORMBLOCKINDEXPROC, glGetUniformBlockIndex, true)      \
       GLEXT(PFNGLUNIFORMBLOCKBINDINGPROC, glUniformBlockBinding, true)        \
       GLEXT(PFNGLGETACTIVEUNIFORMBLOCKIVPROC, glGetActiveUniformBlockiv, true)\
       GLEXT(PFNGLGETACTIVEUNIFORMBLOCKNAMEPROC, glGetActiveUniformBlockName,  \
             true)                                                             \
       GLEXT(PFNGLBINDBUFFERBASEPROC, glBindBufferBase, true)

// TODO(jsanmiya): Get this compiling for all versions of OpenGL. Currently only
//                 valid when GL_VERSION_4_3 is defined.
//       GLEXT(PFNGLPUSHDEBUGGROUPPROC, glPushDebugGroup, false)               \
//       GLEXT(PFNGLPOPDEBUGGROUPPROC, glPopDebugGroup, false)

#      define GLEXT(type, name, required) extern type name;
       GLBASEEXTS
       GLEXTS
#      undef GLEXT
#    endif  // !defined(GL_GLEXT_PROTOTYPES)
#  endif  // !defined(__ANDROID__), so WIN32 & Linux
#endif  // !defined(__APPLE__)

// Note: GLES is enabled for mobile platforms by default, but it can also be
// forcibly enabled for non-mobile platforms.
#ifdef FPLBASE_GLES
// TODO(jsanmiya): Get this compiling for all versions of iOS. Currently only
//                 valid with __OSX_AVAILABLE_STARTING(__MAC_NA,__IPHONE_5_0)
// OpenGL ES extensions function pointers.
// typedef void (*PFNGLPUSHGROUPMARKEREXTPROC)(GLsizei length, const GLchar* message);
// typedef void (*PFNPOPGROUPMARKEREXTPROC)(void);
// #define glPushGroupMarker glPushGroupMarkerEXT
// #define glPopGroupMarker glPopGroupMarkerEXT
/*
#define GLESEXTS                                                               \
      GLEXT(PFNGLPUSHGROUPMARKEREXTPROC, glPushGroupMarkerEXT, false)          \
      GLEXT(PFNPOPGROUPMARKEREXTPROC, glPopGroupMarkerEXT, false)
*/
//
// #define GLEXT(type, name, required) extern type name;
// GLESEXTS
// #undef GLEXT
#  define GLESEXTS
#endif  // FPLBASE_GLES

#ifdef PLATFORM_OSX
#  define glPushGroupMarker glPushGroupMarkerEXT
#  define glPopGroupMarker glPopGroupMarkerEXT
#endif  // PLATFORM_OSX

// Define a GL_CALL macro to wrap each (void-returning) OpenGL call.
// This logs GL error when LOG_GL_ERRORS below is defined.
#if defined(_DEBUG) || DEBUG == 1 || !defined(NDEBUG)
#  define LOG_GL_ERRORS
#endif

#ifdef LOG_GL_ERRORS
#  define GL_CALL(call)                      \
    do {                                     \
      call;                                  \
      LogGLError(__FILE__, __LINE__, #call); \
    } while (0)
#else  // !LOG_GL_ERRORS
#  define GL_CALL(call)                      \
    do {                                     \
      call;                                  \
    } while (0)
#endif  // !LOG_GL_ERRORS

// The error checking function used by the GL_CALL macro above,
// uses glGetError() to check for errors.
extern void LogGLError(const char *file, int line, const char *call);

// These are missing in older NDKs.
#ifndef GL_ETC1_RGB8_OES
#  define GL_ETC1_RGB8_OES 0x8D64
#endif

#ifndef GL_COMPRESSED_RGB8_ETC2
#  define GL_COMPRESSED_RGB8_ETC2 0x9274
#endif

#ifndef GL_COMPRESSED_RGBA_ASTC_4x4_KHR
#  define GL_COMPRESSED_RGBA_ASTC_4x4_KHR 0x93B0
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_5x4_KHR
#  define GL_COMPRESSED_RGBA_ASTC_5x4_KHR 0x93B1
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_5x5_KHR
#  define GL_COMPRESSED_RGBA_ASTC_5x5_KHR 0x93B2
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_6x5_KHR
#  define GL_COMPRESSED_RGBA_ASTC_6x5_KHR 0x93B3
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_6x6_KHR
#  define GL_COMPRESSED_RGBA_ASTC_6x6_KHR 0x93B4
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_8x5_KHR
#  define GL_COMPRESSED_RGBA_ASTC_8x5_KHR 0x93B5
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_8x6_KHR
#  define GL_COMPRESSED_RGBA_ASTC_8x6_KHR 0x93B6
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_8x8_KHR
#  define GL_COMPRESSED_RGBA_ASTC_8x8_KHR 0x93B7
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_10x5_KHR
#  define GL_COMPRESSED_RGBA_ASTC_10x5_KHR 0x93B8
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_10x6_KHR
#  define GL_COMPRESSED_RGBA_ASTC_10x6_KHR 0x93B9
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_10x8_KHR
#  define GL_COMPRESSED_RGBA_ASTC_10x8_KHR 0x93BA
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_10x10_KHR
#  define GL_COMPRESSED_RGBA_ASTC_10x10_KHR 0x93BB
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_12x10_KHR
#  define GL_COMPRESSED_RGBA_ASTC_12x10_KHR 0x93BC
#endif
#ifndef GL_COMPRESSED_RGBA_ASTC_12x12_KHR
#  define GL_COMPRESSED_RGBA_ASTC_12x12_KHR 0x93BD
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR 0x93D0
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR 0x93D1
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR 0x93D2
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR 0x93D3
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR 0x93D4
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR 0x93D5
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR 0x93D6
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR 0x93D7
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR 0x93D8
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR 0x93D9
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR 0x93DA
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR 0x93DB
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR 0x93DC
#endif
#ifndef GL_COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR
#  define GL_COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR 0x93DD
#endif
#ifndef GL_TEXTURE_CUBE_MAP_SEAMLESS
#  define GL_TEXTURE_CUBE_MAP_SEAMLESS 0x884F
#endif

#ifndef GL_INVALID_INDEX
#  define GL_INVALID_INDEX 0xFFFFFFFFu
#endif
#ifndef GL_UNIFORM_BUFFER
#  define GL_UNIFORM_BUFFER 0x8A11
#endif
#ifndef GL_DEPTH_BITS
#  define GL_DEPTH_BITS 0x0D56
#endif
#ifndef GL_LUMINANCE
#  define GL_LUMINANCE 0x1909
#endif
#ifndef GL_LUMINANCE_ALPHA
#  define GL_LUMINANCE_ALPHA 0x190A
#endif

#endif  // FPLBASE_GLPLATFORM_H
