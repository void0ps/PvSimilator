Shader "Custom/TerrainHeightHeatmap"
{
    Properties
    {
        _BaseColor ("Base Color", Color) = (0.5, 0.5, 0.5, 1)
        _LowColor ("Low Height Color", Color) = (0.2, 0.4, 0.8, 1)
        _MidLowColor ("Mid-Low Height Color", Color) = (0.2, 0.7, 0.3, 1)
        _MidHighColor ("Mid-High Height Color", Color) = (0.9, 0.8, 0.2, 1)
        _HighColor ("High Height Color", Color) = (0.9, 0.3, 0.2, 1)
        _MinHeight ("Min Height", Float) = -10
        _MaxHeight ("Max Height", Float) = 10
        _UseVertexColors ("Use Vertex Colors", Float) = 1
        _Smoothness ("Smoothness", Range(0,1)) = 0.3
        _AmbientOcclusion ("Ambient Occlusion", Range(0,1)) = 0.8
    }

    SubShader
    {
        Tags
        {
            "RenderType" = "Opaque"
            "RenderPipeline" = "UniversalPipeline"
            "Queue" = "Geometry"
        }

        LOD 200

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float4 color : COLOR;
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float4 color : TEXCOORD2;
                float2 uv : TEXCOORD3;
                float fogFactor : TEXCOORD4;
            };

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseColor;
                float4 _LowColor;
                float4 _MidLowColor;
                float4 _MidHighColor;
                float4 _HighColor;
                float _MinHeight;
                float _MaxHeight;
                float _UseVertexColors;
                float _Smoothness;
                float _AmbientOcclusion;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;

                VertexPositionInputs vertexInput = GetVertexPositionInputs(input.positionOS.xyz);
                VertexNormalInputs normalInput = GetVertexNormalInputs(input.normalOS);

                output.positionCS = vertexInput.positionCS;
                output.positionWS = vertexInput.positionWS;
                output.normalWS = normalInput.normalWS;
                output.color = input.color;
                output.uv = input.uv;
                output.fogFactor = ComputeFogFactor(vertexInput.positionCS.z);

                return output;
            }

            float4 GetHeightColor(float height)
            {
                float t = saturate((height - _MinHeight) / (_MaxHeight - _MinHeight));

                float4 color;
                if (t < 0.25)
                {
                    color = lerp(_LowColor, _MidLowColor, t * 4.0);
                }
                else if (t < 0.5)
                {
                    color = lerp(_MidLowColor, _MidHighColor, (t - 0.25) * 4.0);
                }
                else if (t < 0.75)
                {
                    color = lerp(_MidHighColor, _HighColor, (t - 0.5) * 4.0);
                }
                else
                {
                    color = lerp(_HighColor, _HighColor * 1.2, (t - 0.75) * 4.0);
                }

                return color;
            }

            half4 frag(Varyings input) : SV_Target
            {
                // 获取基础颜色
                half4 baseColor;
                if (_UseVertexColors > 0.5 && input.color.a > 0.01)
                {
                    // 使用顶点颜色
                    baseColor = input.color;
                }
                else
                {
                    // 基于高度计算颜色
                    baseColor = GetHeightColor(input.positionWS.y);
                }

                // 准备表面数据
                InputData inputData = (InputData)0;
                inputData.positionWS = input.positionWS;
                inputData.normalWS = normalize(input.normalWS);
                inputData.viewDirectionWS = GetWorldSpaceNormalizeViewDir(input.positionWS);
                inputData.shadowMask = 1.0;
                inputData.fogCoord = input.fogFactor;

                // 准备表面数据
                SurfaceData surfaceData = (SurfaceData)0;
                surfaceData.albedo = baseColor.rgb;
                surfaceData.alpha = baseColor.a;
                surfaceData.metallic = 0.0;
                surfaceData.smoothness = _Smoothness;
                surfaceData.occlusion = _AmbientOcclusion;
                surfaceData.emission = 0.0;

                // 计算光照
                half4 color = UniversalFragmentPBR(inputData, surfaceData);

                // 应用雾效
                color.rgb = MixFog(color.rgb, inputData.fogCoord);

                return color;
            }
            ENDHLSL
        }

        // Shadow caster pass
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }

            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull Back

            HLSLPROGRAM
            #pragma vertex ShadowPassVertex
            #pragma fragment ShadowPassFragment

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/ShadowCasterPass.hlsl"

            ENDHLSL
        }

        // Depth pass
        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }

            ZWrite On
            ColorMask 0
            Cull Back

            HLSLPROGRAM
            #pragma vertex DepthOnlyVertex
            #pragma fragment DepthOnlyFragment

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/LitInput.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/Shaders/DepthOnlyPass.hlsl"

            ENDHLSL
        }
    }

    Fallback "Hidden/Universal Render Pipeline/FallbackError"
}
