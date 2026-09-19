import { cn } from "cn"

interface SectionHeadingProps {
  eyebrow?: string
  title: string
  description?: string
  align?: "left" | "center"
  className?: string
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
  className,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3",
        align === "center" && "items-center text-center",
        className
      )}
    >
      {eyebrow && (
        <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">{eyebrow}</p>
      )}
      <h2 className="font-heading text-3xl leading-tight font-semibold tracking-tight text-balance md:text-4xl">
        {title}
      </h2>
      {description && (
        <p
          className={cn(
            "text-base leading-relaxed text-muted-foreground",
            align === "center" ? "max-w-2xl" : "max-w-[65ch]"
          )}
        >
          {description}
        </p>
      )}
    </div>
  )
}