/*
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_FALKEN_H_
#define FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_FALKEN_H_

#include "falken/actions.h"
#include "falken/allocator.h"
#include "falken/attribute.h"
#include "falken/brain.h"
#include "falken/brain_spec.h"
#include "falken/config.h"
#include "falken/entity.h"
#include "falken/episode.h"
#include "falken/log.h"
#include "falken/observations.h"
#include "falken/primitives.h"
#include "falken/service.h"
#include "falken/session.h"

/**
@mainpage
Falken provides developers with a service that allows them to train AI that can
play and test their games. Unlike traditional RL frameworks that learn through
rewards or batches of offline training, Falken is based on training AI via
realtime, human interactions.

Because human time is precious, the system is designed to seamlessly transition
between humans playing the game (training) and the AI playing the game
(inference). This allows us to support a variety of training styles, from
providing a large batch of demonstrations up front to providing “just in time”
demonstrations when the AI encounters a state it does not know how to handle.

Behind the scenes, Falken automatically handles logging of experience, separates
out human demonstrations, trains new models (including hyper parameter search),
serves the best models for on-device inference, and maintains a version history.
*/

#endif  // RESEARCH_KERNEL_FALKEN_SDK_CORE_PUBLIC_INCLUDE_FALKEN_FALKEN_H_
