/**
 * PostProcessing.tsx - Visual effects (bloom, DOF, vignette)
 * Adds cinematic polish to the flyover
 */

import {
  EffectComposer,
  Bloom,
  Vignette,
  DepthOfField,
  ChromaticAberration,
} from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import type { WeatherPreset } from './Atmosphere';

interface PostProcessingProps {
  preset: WeatherPreset;
  phase: 'approach' | 'fieldReveal' | 'fieldSwoop' | 'branding';
  enabled?: boolean;
}

export function PostProcessing({
  preset,
  phase,
  enabled = true,
}: PostProcessingProps) {
  if (!enabled) return null;

  // Adjust effects based on preset and phase
  const bloomIntensity = preset === 'night' ? 1.5 : preset === 'sunset' ? 0.8 : 0.3;
  const vignetteIntensity = phase === 'approach' ? 0.6 : 0.3;
  const dofEnabled = phase === 'approach';

  return (
    <EffectComposer>
      <Bloom
        intensity={bloomIntensity}
        luminanceThreshold={0.6}
        luminanceSmoothing={0.9}
        mipmapBlur
      />
      <Vignette
        offset={0.3}
        darkness={vignetteIntensity}
        blendFunction={BlendFunction.NORMAL}
      />
      {dofEnabled ? (
        <DepthOfField
          focusDistance={0.02}
          focalLength={0.05}
          bokehScale={3}
        />
      ) : (
        <Bloom intensity={0} />
      )}
      <ChromaticAberration
        offset={[0.0005, 0.0005] as [number, number]}
        blendFunction={BlendFunction.NORMAL}
        radialModulation={false}
        modulationOffset={0}
      />
    </EffectComposer>
  );
}
