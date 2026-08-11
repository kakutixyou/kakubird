// handlers/IMessageHandler.ts

export interface IMessageHandler<T = any> {
    execute(message: T): Promise<void>;
}