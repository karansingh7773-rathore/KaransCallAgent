import { useState, useEffect, useRef, useCallback } from 'react';
import { LiveKitRoom, RoomAudioRenderer, useRoomContext, useVoiceAssistant, useTrackVolume } from '@livekit/components-react';
import { ConnectionState } from 'livekit-client';
import { AssistantState } from './types';
import { Header } from './components/Header';
import { ConversationBox } from './components/ConversationBox';
import { ChatInput } from './components/ChatInput';
import { ControlPanel } from './components/ControlPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { StartupDialog } from './components/StartupDialog';
import { Activity, Phone } from 'lucide-react';

// --- Components inside LiveKitRoom ---

interface RoomHandlerProps {
    ttsVoice: string;
    agentPrompt: string;
    businessDetails: string;
}

// Handles Room logic: voice switching + prompt updates + audio rendering
function RoomHandler({ ttsVoice, agentPrompt, businessDetails }: RoomHandlerProps) {
    const room = useRoomContext();
    const lastVoiceRef = useRef<string>(ttsVoice);
    const lastPromptRef = useRef<string>(agentPrompt);
    const lastBusinessRef = useRef<string>(businessDetails);

    // Initial Setup
    useEffect(() => {
        if (room.state === ConnectionState.Connected) {
            room.localParticipant.setMicrophoneEnabled(true).catch(console.error);

            // Set all initial attributes
            room.localParticipant.setAttributes({
                tts_voice: ttsVoice,
                agent_prompt: agentPrompt,
                business_details: businessDetails
            }).catch(console.error);
        }
    }, [room.state]);

    // Watch for Voice changes
    useEffect(() => {
        if (room.state === ConnectionState.Connected && ttsVoice !== lastVoiceRef.current) {
            room.localParticipant.setAttributes({ tts_voice: ttsVoice }).catch(console.error);
            lastVoiceRef.current = ttsVoice;
            console.log('[LiveKit] Voice updated:', ttsVoice);
        }
    }, [ttsVoice, room.state]);

    // Watch for Prompt/Business changes
    useEffect(() => {
        if (room.state === ConnectionState.Connected) {
            const hasChanged = agentPrompt !== lastPromptRef.current || businessDetails !== lastBusinessRef.current;
            if (hasChanged) {
                room.localParticipant.setAttributes({
                    agent_prompt: agentPrompt,
                    business_details: businessDetails
                }).catch(console.error);
                lastPromptRef.current = agentPrompt;
                lastBusinessRef.current = businessDetails;
                console.log('[LiveKit] Prompt/Business context updated');
            }
        }
    }, [agentPrompt, businessDetails, room.state]);

    return <RoomAudioRenderer />;
}

// Custom Pulse Visualizer (Orb Style)
function PulseVisualizer({ trackRef, state }: any) {
    const volume = useTrackVolume(trackRef);
    const [smoothVol, setSmoothVol] = useState(0);

    // Smooth out volume for nicer animation
    useEffect(() => {
        if (volume !== undefined) {
            setSmoothVol(prev => prev * 0.8 + volume * 0.2);
        }
    }, [volume]);

    const isTalking = state === 'speaking';

    // Scale factor based on volume (0.0 to 1.0) -> Scale (1.0 to 1.5)
    // Multiplied by 3 for visible effect
    const scale = 1 + Math.max(0, smoothVol * 4);
    const glowOpacity = Math.min(1, smoothVol * 3);

    return (
        <div className="relative flex items-center justify-center w-64 h-64" style={{ contain: 'layout' }}>
            {/* 1. Outer Ripple (Echo) */}
            <div
                className="absolute inset-0 rounded-full bg-orange-500/20 blur-xl transition-all duration-100 ease-out"
                style={{
                    transform: isTalking ? `scale(${scale * 1.2})` : 'scale(0.8)',
                    opacity: isTalking ? glowOpacity * 0.5 : 0
                }}
            />

            {/* 2. Inner Glow Ring */}
            <div
                className="absolute inset-8 rounded-full border-2 border-orange-500/30 blur-sm transition-all duration-75"
                style={{
                    transform: isTalking ? `scale(${scale})` : 'scale(1)',
                    opacity: isTalking ? glowOpacity : 0.1
                }}
            />

            {/* 3. Core Orb Container */}
            <div className="relative w-32 h-32 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center shadow-2xl z-10 transition-all duration-300">
                {/* Waveform Icon */}
                {isTalking ? (
                    // Animated Waveform
                    <div className="flex items-center gap-1 h-8">
                        {[0, 1, 2, 3, 4].map(i => (
                            <div
                                key={i}
                                className="w-1 bg-orange-500 rounded-full transition-all duration-75"
                                style={{
                                    height: `${12 + Math.random() * 24 * scale}px`,
                                    opacity: 0.8 + glowOpacity * 0.2
                                }}
                            />
                        ))}
                    </div>
                ) : (
                    // Resting Icon
                    <Activity className="w-8 h-8 text-zinc-600" />
                )}
            </div>
        </div>
    );
}


// The Visualizer component wrapper
function AgentVisualizer() {
    const { state, audioTrack } = useVoiceAssistant();

    return (
        <div className="w-full h-[400px] flex items-center justify-center relative flex-col">
            {/* Visualizer Orb */}
            <div className="mb-8">
                {audioTrack ? (
                    <PulseVisualizer
                        trackRef={audioTrack}
                        state={state}
                    />
                ) : (
                    // Connecting / Idle State
                    <div className="relative flex items-center justify-center w-64 h-64">
                        <div className="w-32 h-32 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                            <Activity className="w-8 h-8 text-zinc-700 animate-pulse" />
                        </div>
                    </div>
                )}
            </div>

            {/* State Text */}
            <div className="absolute bottom-12 text-zinc-500 text-sm font-medium tracking-wide uppercase">
                {state === 'speaking' ? 'Agent Speaking' : state === 'listening' ? 'Listening...' : 'Ready'}
            </div>
        </div>
    );
}


// --- Main App Component ---

function App() {
    const [state, setState] = useState<AssistantState>('IDLE');
    const [isMicActive, setIsMicActive] = useState(false);

    // LiveKit connection info
    const [liveKitToken, setLiveKitToken] = useState<string | null>(null);
    const [liveKitUrl, setLiveKitUrl] = useState<string | null>(null);
    const [isConnecting, setIsConnecting] = useState(false);

    const ws = useRef<WebSocket | null>(null);

    // WebSocket logic
    useEffect(() => {
        const connectWebSocket = () => {
            ws.current = new WebSocket('ws://localhost:8000/ws');
            ws.current.onopen = () => console.log('Connected to Server (text)');
            ws.current.onmessage = (event) => console.log('WS msg:', event.data);
            ws.current.onclose = () => setTimeout(connectWebSocket, 3000);
        };
        connectWebSocket();
        return () => ws.current?.close();
    }, []);

    const sendMessage = (text: string) => {
        ws.current?.send(JSON.stringify({ type: 'text', data: text }));
    };

    // LiveKit Voice Control
    const toggleMic = async () => {
        if (liveKitToken) {
            setLiveKitToken(null);
            setLiveKitUrl(null);
            setIsMicActive(false);
            setState('IDLE');
        } else {
            setIsConnecting(true);
            try {
                const response = await fetch('http://localhost:8000/api/livekit-token', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        identity: `user-${Date.now()}`,
                        room: 'voice-assistant'
                    })
                });
                const data = await response.json();
                if (data.error) throw new Error(data.error);

                setLiveKitUrl(data.url);
                setLiveKitToken(data.token);
                setIsMicActive(true);
                setState('LISTENING');
            } catch (err) {
                console.error(err);
            } finally {
                setIsConnecting(false);
            }
        }
    };

    const handleConnected = useCallback(() => {
        setIsMicActive(true);
        setState('LISTENING');
    }, []);

    const handleDisconnected = useCallback(() => {
        setLiveKitToken(null);
        setLiveKitUrl(null);
        setIsMicActive(false);
        setState('IDLE');
    }, []);

    // Deepgram voice state (persisted)
    const [ttsVoice, setTtsVoice] = useState(() => localStorage.getItem('tts_voice') || 'arcas');
    const [showSettings, setShowSettings] = useState(false);

    // Config state (NOT persisted - clears on refresh)
    const [agentPrompt, setAgentPrompt] = useState("");
    const [businessDetails, setBusinessDetails] = useState("");

    // Save voice preference to localStorage
    useEffect(() => {
        localStorage.setItem('tts_voice', ttsVoice);
    }, [ttsVoice]);


    // Resizing State
    const [sidebarWidth, setSidebarWidth] = useState(600);
    const [isResizing, setIsResizing] = useState(false);
    const sidebarRef = useRef<HTMLDivElement>(null);

    const startResizing = (e: React.MouseEvent) => {
        setIsResizing(true);
        e.preventDefault();
    };

    useEffect(() => {
        const stopResizing = () => setIsResizing(false);
        const resize = (e: MouseEvent) => {
            if (isResizing) {
                const newWidth = window.innerWidth - e.clientX;
                if (newWidth >= 300 && newWidth <= 900) setSidebarWidth(newWidth);
            }
        };
        if (isResizing) {
            window.addEventListener('mousemove', resize);
            window.addEventListener('mouseup', stopResizing);
        }
        return () => {
            window.removeEventListener('mousemove', resize);
            window.removeEventListener('mouseup', stopResizing);
        };
    }, [isResizing]);

    const isLiveKitConnected = liveKitToken && liveKitUrl;

    const renderMainStage = () => (
        <div className="flex-1 flex flex-col items-center justify-center p-8 gap-6 pb-32 relative">
            {isLiveKitConnected ? (
                <AgentVisualizer />
            ) : (
                <div className="w-full h-[400px] flex items-center justify-center relative flex-col">
                    <div className="relative flex items-center justify-center w-64 h-64 mb-8">
                        <div className="w-32 h-32 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center shadow-lg">
                            <Phone className="w-8 h-8 text-zinc-600" />
                        </div>
                    </div>
                    <div className="text-zinc-500 text-sm font-medium tracking-wide uppercase">
                        {isConnecting ? 'Connecting...' : 'Calling Agent Ready'}
                    </div>
                </div>
            )}

            <div className="z-20">
                <ControlPanel
                    isMicActive={isMicActive}
                    toggleMic={toggleMic}
                    state={state}
                />
            </div>
        </div>
    );

    const renderSidebar = () => (
        <aside
            ref={sidebarRef}
            style={{ width: sidebarWidth }}
            className="relative border border-zinc-700/50 bg-zinc-900/80 backdrop-blur-xl flex flex-col shadow-2xl z-30 h-[calc(100%-3rem)] my-auto mr-4 rounded-[2rem] overflow-hidden transition-[width] duration-0 ease-linear p-2"
        >
            <div className="absolute left-0 top-0 bottom-0 w-2 cursor-col-resize z-50 hover:bg-orange-500/20" onMouseDown={startResizing} />

            <div className="flex-1 flex flex-col w-full h-full rounded-[1.5rem] border border-zinc-700/50 overflow-hidden bg-zinc-900/50">
                <div className="p-5 border-b border-zinc-800 bg-zinc-900/50 flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-zinc-300 uppercase flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${isMicActive ? 'bg-green-500' : 'bg-orange-500'}`}></span>
                        Conversation
                    </h2>
                </div>

                <div className="flex-1 overflow-hidden relative flex flex-col">
                    {isLiveKitConnected ? (
                        <ConversationBox />
                    ) : (
                        <div className="flex-1 flex items-center justify-center text-zinc-500 text-sm p-4 text-center">
                            🎙️ Connect to start call
                        </div>
                    )}
                </div>

                <div className="p-5 border-t border-zinc-700/50 bg-zinc-900/50">
                    <ChatInput onSendMessage={sendMessage} />
                </div>
            </div>
        </aside>
    );

    return (
        <div className="flex flex-col h-full font-sans text-zinc-100 bg-zinc-950 relative z-20"
            style={{ cursor: isResizing ? 'col-resize' : 'default' }}>
            <StartupDialog />
            <Header state={state} onSettingsClick={() => setShowSettings(true)} />

            <SettingsPanel
                isOpen={showSettings}
                onClose={() => setShowSettings(false)}
                ttsVoice={ttsVoice}
                onChangeTtsVoice={setTtsVoice}
                agentPrompt={agentPrompt}
                onChangeAgentPrompt={setAgentPrompt}
                businessDetails={businessDetails}
                onChangeBusinessDetails={setBusinessDetails}
            />

            <div className="flex-1 flex overflow-hidden relative bg-zinc-950">
                {isLiveKitConnected ? (
                    <LiveKitRoom
                        token={liveKitToken!}
                        serverUrl={liveKitUrl!}
                        connect={true}
                        audio={true}
                        video={false}
                        onConnected={handleConnected}
                        onDisconnected={handleDisconnected}
                        className="flex-1 flex overflow-hidden relative"
                    >
                        <RoomHandler
                            ttsVoice={ttsVoice}
                            agentPrompt={agentPrompt}
                            businessDetails={businessDetails}
                        />
                        {renderMainStage()}
                        {renderSidebar()}
                    </LiveKitRoom>
                ) : (
                    <>
                        {renderMainStage()}
                        {renderSidebar()}
                    </>
                )}
            </div>
        </div>
    );
}

export default App;
