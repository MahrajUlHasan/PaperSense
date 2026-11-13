import { formatTime } from "@/lib/format";
import type { ChatMessage } from "@/lib/types";

export function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="bg-secondary max-w-[85%] rounded-lg rounded-br-sm px-4 py-2.5 whitespace-pre-wrap">
        {message.content}
      </div>
      <time className="text-muted-foreground text-xs" dateTime={message.createdAt}>
        {formatTime(message.createdAt)}
      </time>
    </div>
  );
}
