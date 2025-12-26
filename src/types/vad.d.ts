// Global VAD types loaded from CDN
declare global {
    interface Window {
        vad: {
            MicVAD: {
                // Static factory method
                new: (options: any) => Promise<any>;
            };
            utils: {
                arrayBufferToBase64: (buffer: ArrayBuffer) => string;
            };
        };
    }
}

export { };
