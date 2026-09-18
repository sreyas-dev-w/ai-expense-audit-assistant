import { QuoteIcon } from "@/components/icons"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatPercent } from "@/lib/format"
import type { PolicyReference } from "@/lib/types/api"

export function GroundingReferences({ references }: { references: PolicyReference[] }) {
  if (references.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>Policy citations</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <Accordion type="multiple" className="w-full">
          {references.map((ref, i) => (
            <AccordionItem key={`${ref.chunk_id}-${i}`} value={`ref-${i}`} className="px-(--card-spacing)">
              <AccordionTrigger className="text-sm">
                <span className="flex items-center gap-2">
                  <QuoteIcon className="size-3.5 text-muted-foreground" />
                  Policy #{ref.policy_id} · chunk {ref.chunk_id}
                  {ref.similarity_score !== null && (
                    <span className="text-xs text-muted-foreground">
                      {formatPercent(ref.similarity_score)} match
                    </span>
                  )}
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <blockquote className="border-l-2 border-primary/30 pl-3 text-sm leading-relaxed text-muted-foreground">
                  {ref.content}
                </blockquote>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </CardContent>
    </Card>
  )
}
