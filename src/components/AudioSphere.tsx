import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { AssistantState } from '../types';

interface AudioSphereProps {
    state: AssistantState;
    micAnalyser?: AnalyserNode | null;
    playbackAnalyser?: AnalyserNode | null;
}

export function AudioSphere({ state, micAnalyser, playbackAnalyser }: AudioSphereProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
    const materialRef = useRef<THREE.ShaderMaterial | null>(null);
    const animationIdRef = useRef<number | null>(null);
    const glowRef = useRef<HTMLDivElement>(null);

    // Keep track of latest props for the animation loop
    const propsRef = useRef({ state, micAnalyser, playbackAnalyser });
    useEffect(() => {
        propsRef.current = { state, micAnalyser, playbackAnalyser };
    }, [state, micAnalyser, playbackAnalyser]);

    useEffect(() => {
        if (!containerRef.current) return;

        // 1. Basic Setup
        const scene = new THREE.Scene();

        // Standard camera setup
        const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
        camera.position.z = 2.8;

        const renderer = new THREE.WebGLRenderer({
            alpha: true, // Transparent background
            antialias: true
        });
        rendererRef.current = renderer;

        // Initial Size
        const updateSize = () => {
            if (!containerRef.current || !rendererRef.current) return;
            const width = containerRef.current.clientWidth;
            const height = containerRef.current.clientHeight;

            // Protect against 0 height/width which can happen during layout
            if (width === 0 || height === 0) return;

            renderer.setSize(width, height);
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
        };

        containerRef.current.appendChild(renderer.domElement);

        // Use ResizeObserver for robust layout tracking
        const resizeObserver = new ResizeObserver(() => {
            updateSize();
        });
        resizeObserver.observe(containerRef.current);

        // Initial call
        updateSize();

        // 2. Geometry
        const geometry = new THREE.SphereGeometry(1, 128, 128);

        // 3. Shader Material
        const vertexShader = `
            uniform float uTime;
            uniform float uFrequency;
            varying vec3 vNormal;
            varying vec3 vViewPosition;

            // Simplex 3D Noise 
            // by Ian McEwan, Ashima Arts
            vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x, 289.0);}
            vec4 taylorInvSqrt(vec4 r){return 1.79284291400159 - 0.85373472095314 * r;}

            float snoise(vec3 v){ 
                const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
                const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);

                // First corner
                vec3 i  = floor(v + dot(v, C.yyy) );
                vec3 x0 = v - i + dot(i, C.xxx) ;

                // Other corners
                vec3 g = step(x0.yzx, x0.xyz);
                vec3 l = 1.0 - g;
                vec3 i1 = min( g.xyz, l.zxy );
                vec3 i2 = max( g.xyz, l.zxy );

                //  x0 = x0 - 0.0 + 0.0 * C 
                vec3 x1 = x0 - i1 + 1.0 * C.xxx;
                vec3 x2 = x0 - i2 + 2.0 * C.xxx;
                vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;

                // Permutations
                i = mod(i, 289.0 ); 
                vec4 p = permute( permute( permute( 
                            i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
                        + i.y + vec4(0.0, i1.y, i2.y, 1.0 )) 
                        + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));

                // Gradients
                float n_ = 1.0/7.0; // N=7
                vec3  ns = n_ * D.wyz - D.xzx;

                vec4 j = p - 49.0 * floor(p * ns.z *ns.z);  //  mod(p,N*N)

                vec4 x_ = floor(j * ns.z);
                vec4 y_ = floor(j - 7.0 * x_ );    // mod(j,N)

                vec4 x = x_ *ns.x + ns.yyyy;
                vec4 y = y_ *ns.x + ns.yyyy;
                vec4 h = 1.0 - abs(x) - abs(y);

                vec4 b0 = vec4( x.xy, y.xy );
                vec4 b1 = vec4( x.zw, y.zw );

                vec4 s0 = floor(b0)*2.0 + 1.0;
                vec4 s1 = floor(b1)*2.0 + 1.0;
                vec4 sh = -step(h, vec4(0.0));

                vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
                vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;

                vec3 p0 = vec3(a0.xy,h.x);
                vec3 p1 = vec3(a0.zw,h.y);
                vec3 p2 = vec3(a1.xy,h.z);
                vec3 p3 = vec3(a1.zw,h.w);

                //Normalise gradients
                vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
                p0 *= norm.x;
                p1 *= norm.y;
                p2 *= norm.z;
                p3 *= norm.w;

                // Mix final noise value
                vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
                m = m * m;
                return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), 
                                                dot(p2,x2), dot(p3,x3) ) );
            }

            void main() {
                vNormal = normal;
                
                // Calculate Noise
                float noise = snoise(position * 2.0 + uTime * 0.5);
                
                // Displace vertices based on noise and audio frequency
                float distortion = noise * (0.1 + uFrequency * 0.6); 
                vec3 newPosition = position + (normal * distortion);

                vec4 mvPosition = modelViewMatrix * vec4(newPosition, 1.0);
                vViewPosition = -mvPosition.xyz;
                gl_Position = projectionMatrix * mvPosition;
            }
        `;

        const fragmentShader = `
            varying vec3 vNormal;
            varying vec3 vViewPosition;

            void main() {
                // Calculate Fresnel (Rim Light)
                vec3 normal = normalize(vNormal);
                vec3 viewDir = normalize(vViewPosition); // Camera is at 0,0,0 in view space? viewPosition is -mvPosition
                
                float fresnel = dot(normal, viewDir);
                
                // Invert fresnel for rim effect and sharpen it
                fresnel = clamp(1.0 - fresnel, 0.0, 1.0);
                fresnel = pow(fresnel, 5.0); // Higher power = thinner line

                // Color: Black body + White rim
                vec3 finalColor = vec3(0.0) + vec3(fresnel); 

                gl_FragColor = vec4(finalColor, 1.0);
            }
        `;

        const material = new THREE.ShaderMaterial({
            uniforms: {
                uTime: { value: 0 },
                uFrequency: { value: 0.0 },
            },
            vertexShader,
            fragmentShader,
        });
        materialRef.current = material;

        const sphere = new THREE.Mesh(geometry, material);
        scene.add(sphere);

        // 4. Animation Loop
        const animate = () => {
            animationIdRef.current = requestAnimationFrame(animate);

            material.uniforms.uTime.value += 0.01;

            // Access current props via ref
            const { state, micAnalyser, playbackAnalyser } = propsRef.current;

            // Audio Data Logic
            let activeAnalyser = null;
            if (state === 'LISTENING' && micAnalyser) {
                activeAnalyser = micAnalyser;
            } else if (state === 'SPEAKING' && playbackAnalyser) {
                activeAnalyser = playbackAnalyser;
            }

            let frequencyFactor = 0;
            // Separate check for "Output Energy" specifically for the glow
            let outputEnergy = 0;

            if (activeAnalyser) {
                const bufferLength = activeAnalyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                activeAnalyser.getByteFrequencyData(dataArray);

                // Calculate average or peak
                let sum = 0;
                // Use lower half of freq range (more energy usually)
                const relevantBins = Math.floor(bufferLength * 0.5);
                for (let i = 0; i < relevantBins; i++) {
                    sum += dataArray[i];
                }
                const avg = sum / relevantBins; // 0-255
                frequencyFactor = avg / 255;
            } else {
                // Idle state
                frequencyFactor = 0.05;
            }

            // Calculate output energy explicitly from playbackAnalyser if available
            if (playbackAnalyser) {
                const bufferLength = playbackAnalyser.frequencyBinCount;
                const dataArray = new Uint8Array(bufferLength);
                playbackAnalyser.getByteFrequencyData(dataArray);
                let sum = 0;
                for (let i = 0; i < bufferLength; i++) sum += dataArray[i];
                outputEnergy = (sum / bufferLength) / 255;
            }

            // Lerp for smoothness
            const target = frequencyFactor;
            const current = material.uniforms.uFrequency.value;
            material.uniforms.uFrequency.value += (target - current) * 0.1;

            renderer.render(scene, camera);

            // GLOW LOGIC (Direct DOM access for performance)
            if (glowRef.current) {
                // Glow active if outputEnergy is significant OR state implies speaking
                // We use a low threshold for outputEnergy to catch quiet speaking parts
                const isSpeaking = (state === 'SPEAKING') || (outputEnergy > 0.01);

                if (isSpeaking) {
                    glowRef.current.style.opacity = '1';
                    glowRef.current.style.transform = 'scale(1.2)';
                } else {
                    glowRef.current.style.opacity = '0';
                    glowRef.current.style.transform = 'scale(0.8)';
                }
            }
        };

        animate();

        // Cleanup
        return () => {
            resizeObserver.disconnect();
            if (animationIdRef.current) cancelAnimationFrame(animationIdRef.current);
            if (containerRef.current && renderer.domElement) {
                containerRef.current.removeChild(renderer.domElement);
            }
            geometry.dispose();
            material.dispose();
            renderer.dispose();
        };
    }, []);

    return (
        <div className="relative w-full h-full min-h-[300px] flex items-center justify-center">
            {/* Background Glow - Controlled by Ref for perfect sync */}
            <div
                ref={glowRef}
                className="absolute w-[500px] h-[500px] bg-white/30 rounded-full blur-[100px] transition-all duration-300 ease-out pointer-events-none opacity-0 scale-75"
            />
            {/* Three.js Container */}
            <div ref={containerRef} className="w-full h-full relative z-10" />
        </div>
    );
}
