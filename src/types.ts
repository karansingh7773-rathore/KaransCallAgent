export type AssistantState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'SPEAKING';

export interface ChatMessage {
    role: 'user' | 'assistant';
    text: string;
}
