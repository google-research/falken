using UnityEngine;
using UnityEngine.Rendering.PostProcessing;

namespace VertexFragment
{
    [PostProcess(typeof(SobelOutlineRenderer), PostProcessEvent.BeforeStack, "SobelOutline")]
    public class SobelOutline : PostProcessEffectSettings
    {
        [Tooltip("Thickness of the Sobel Outline")]
        public FloatParameter thickness = new FloatParameter { value = 1.0f };

        [Tooltip("Multiplier of the Depth-Component of the Sobel Outline")]
        public FloatParameter depthMultiplier = new FloatParameter { value = 1.0f };

        [Tooltip("Bias of the Depth-Component of the Sobel Outline")]
        public FloatParameter depthBias = new FloatParameter { value = 1.0f };

        [Tooltip("Filters out the Depth-Component based on the normal angle.")]
        public FloatParameter depthFacing = new FloatParameter { value = 1.0f };

        [Tooltip("Multiplier of the Normal-Component of the Sobel Outline")]
        public FloatParameter normalMultiplier = new FloatParameter { value = 1.0f };

        [Tooltip("Bias of the Normal-Component of the Sobel Outline")]
        public FloatParameter normalBias = new FloatParameter { value = 10.0f };

        [Tooltip("Color of the Sobel Outline")]
        public ColorParameter color = new ColorParameter { value = Color.black };
    }

    public sealed class SobelOutlineRenderer : PostProcessEffectRenderer<SobelOutline>
    {
        public const string SobelShader = "VertexFragment/SobelOutlineCg";

        public override void Render(PostProcessRenderContext context)
        {
            var shader = Shader.Find(SobelShader);

            if (shader == null)
            {
                Debug.LogError($"Failed to get shader '{SobelShader}' for Sobel Outline Post-Processing");
                return;
            }

            var sheet = context.propertySheets.Get(shader);

            if (sheet == null)
            {
                Debug.LogError($"Failed to get PropertySheet for Sobel Outline Post-Processing effect.");
                return;
            }

            sheet.properties.SetFloat("_OutlineThickness", settings.thickness);
            sheet.properties.SetFloat("_OutlineDepthMultiplier", settings.depthMultiplier);
            sheet.properties.SetFloat("_OutlineDepthBias", settings.depthBias);
            sheet.properties.SetFloat("_OutlineDepthFacing", settings.depthFacing);
            sheet.properties.SetFloat("_OutlineNormalMultiplier", settings.normalMultiplier);
            sheet.properties.SetFloat("_OutlineNormalBias", settings.normalBias);
            sheet.properties.SetColor("_OutlineColor", settings.color);

            sheet.properties.SetVector("_CameraWorldPos", context.camera.transform.position);
            Matrix4x4 mat = (context.camera.projectionMatrix * context.camera.worldToCameraMatrix).inverse;
            sheet.properties.SetMatrix("_ViewProjectInverse", mat);

            context.command.BlitFullscreenTriangle(context.source, context.destination, sheet, 0);
        }
    }
}