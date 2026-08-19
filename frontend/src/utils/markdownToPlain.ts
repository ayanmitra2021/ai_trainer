/**
 * markdownToPlain — Phase 18.6
 * Strips Markdown syntax for TTS input. Simple regex, no parser dependency.
 */

export function markdownToPlain(md: string): string {
  return md
    // Remove headings markers
    .replace(/^#{1,6}\s+/gm, "")
    // Convert links to just the text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    // Remove bold/italic markers
    .replace(/\*{1,3}([^*]+)\*{1,3}/g, "$1")
    .replace(/_{1,3}([^_]+)_{1,3}/g, "$1")
    // Remove inline code
    .replace(/`([^`]+)`/g, "$1")
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, "")
    // Remove blockquote markers
    .replace(/^>\s*/gm, "")
    // Remove horizontal rules
    .replace(/^---+$/gm, "")
    // Remove bullet markers
    .replace(/^[-*+]\s+/gm, "")
    // Remove numbered list markers
    .replace(/^\d+\.\s+/gm, "")
    // Remove bare URLs
    .replace(/https?:\/\/\S+/g, "")
    // Collapse multiple blank lines
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
