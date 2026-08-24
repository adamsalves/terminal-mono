{{- /* The markdown twin of a post, published next to it as index.md.

       Two things want this. A reader that is an answer engine gets the source
       without having to strip a page's chrome back off it, and a citation that
       lands here lands on the same words the HTML shows rather than on a
       reconstruction of them.

       The metadata is a plain list rather than a YAML front-matter block. This
       file is read as prose by a model, not parsed by a static-site generator,
       and fenced front matter is a delimiter the reader has to know about
       before the first line means anything.

       .RawContent, not .Plain, for the reason llms-full.txt gives: headings,
       lists and code fences are the structure, and .Plain is what is left over
       after throwing them away. */ -}}
{{- $out := slice (printf "# %s" .Title) "" -}}
{{- $out = $out | append (printf "- URL: %s" .Permalink) -}}
{{- with .Description }}{{ $out = $out | append (printf "- Summary: %s" (. | plainify | strings.TrimSpace)) }}{{ end -}}
{{- if not .Date.IsZero }}{{ $out = $out | append (printf "- Published: %s" (.Date.Format "2006-01-02")) }}{{ end -}}
{{- if not .Lastmod.IsZero }}{{ $out = $out | append (printf "- Updated: %s" (.Lastmod.Format "2006-01-02")) }}{{ end -}}
{{- $tags := partial "params-list.html" (dict "value" .Params.tags "path" (printf "tags in %s" .RelPermalink) "maps" false) -}}
{{- with $tags }}{{ $out = $out | append (printf "- Tags: %s" (delimit . ", ")) }}{{ end -}}
{{- $out = $out | append (printf "- Words: %d" .WordCount) -}}
{{- $out = $out | append (printf "- Language: %s" (or .Language.Locale .Language.Lang)) -}}
{{- with .Translations -}}
  {{- range . -}}
    {{- $out = $out | append (printf "- Also published in %s: %s" (or .Language.Locale .Language.Lang) .Permalink) -}}
  {{- end -}}
{{- end -}}
{{- $out = $out | append "" (.RawContent | strings.TrimSpace) -}}
{{ delimit $out "\n" }}
