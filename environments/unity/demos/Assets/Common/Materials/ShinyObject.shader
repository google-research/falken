Shader "Custom/ShinyObject"
{
    Properties
    {
        _Color ("Color", Color) = (1,1,1,1)
        _Cube ("Cubemap", CUBE) = "" {}
        _Reflectivity ("Reflectivity", Range(0,2)) = 1.0
        _Fresnel ("Fresnel", Range(0,5)) = 1.0
        _LodLevel ("LOD Level", Range(0, 10)) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        LOD 200

        CGPROGRAM
        // Physically based Standard lighting model, and enable shadows on all light types
        #pragma surface surf Standard fullforwardshadows

        // Use shader model 3.0 target, to get nicer looking lighting
        #pragma target 3.0

        struct Input
        {
            float3 worldRefl;
            float3 worldNormal;
            float3 viewDir;
        };

        half _Reflectivity;
        float _Fresnel;
        float _LodLevel;
        fixed4 _Color;
        samplerCUBE _Cube;

        void surf (Input IN, inout SurfaceOutputStandard o)
        {
            o.Albedo = _Color.rgb;
            float3 reflectionVector = WorldReflectionVector(IN, o.Normal);
            fixed4 envMap = texCUBElod(_Cube, float4(reflectionVector, _LodLevel)) * _Reflectivity;
            float fresnel = 1 - saturate(dot(IN.worldNormal, IN.viewDir));
            fresnel = pow(fresnel, _Fresnel);
            o.Emission = envMap * fresnel;
            o.Alpha = 1;
        }
        ENDCG
    }
    FallBack "Diffuse"
}
