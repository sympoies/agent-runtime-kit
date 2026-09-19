#!/usr/bin/env bash
# Validate the SUPPORT_MATRIX surface registry shape.
#
# This focused smoke check covers the schema constraints that matter for
# `agent-runtime render --target support-matrix`: 16 canonical surfaces, all
# three products (codex, claude, hermes) present, typed acceptance entries,
# exactly one command/note per entry, and exit-status-only success predicates.
#
# It also resolves every `source_manifest` provenance citation: each entry must
# be `path` or `path#anchor` (the legacy `path:Lstart-Lend` line-number form is
# rejected), the path must exist, and an `#anchor` must resolve to a Markdown
# heading (`.md`) or a YAML key. This keeps surface provenance from silently
# rotting into dead links the way line-number citations did.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$ROOT/manifests/surfaces.yaml"
EXECUTE_ACCEPTANCE=0

for arg in "$@"; do
  case "$arg" in
    --execute-acceptance)
      EXECUTE_ACCEPTANCE=1
      ;;
    -*)
      echo "validate-surfaces-manifest: unknown option $arg" >&2
      exit 64
      ;;
    *)
      MANIFEST="$arg"
      ;;
  esac
done

ruby - "$MANIFEST" "$ROOT" "$EXECUTE_ACCEPTANCE" <<'RUBY'
require "open3"
require "yaml"

path = ARGV.fetch(0)
root = ARGV.fetch(1)
execute_acceptance = ARGV.fetch(2) == "1"

STATE_VALUES = %w[
  shipped
  partial
  planned-not-shipped
  not-shipped
  not-applicable
].freeze

def fail_with(message)
  warn "validate-surfaces-manifest: #{message}"
  exit 1
end

# GitHub-flavored Markdown heading slug: lowercase, drop characters that are
# not alphanumeric / space / hyphen, then collapse whitespace runs to a single
# hyphen. Used to resolve `path.md#anchor` source_manifest citations.
def gfm_slug(text)
  text.downcase.gsub(/[^a-z0-9 \-]/, "").strip.gsub(/\s+/, "-")
end

def markdown_heading_slugs(abs_path)
  slugs = []
  File.foreach(abs_path) do |line|
    next unless (m = line.match(/^\#{1,6}\s+(\S.*?)\s*\z/))

    slugs << gfm_slug(m[1])
  end
  slugs
end

def yaml_key?(abs_path, anchor)
  File.foreach(abs_path).any? { |line| line =~ /^\s*#{Regexp.escape(anchor)}:/ }
end

# Resolve one `source_manifest` citation. Format is `path` or `path#anchor`;
# the legacy `path:Lstart-Lend` line-number form is rejected so provenance
# cannot silently rot when a cited file's line layout shifts. The path must
# exist, and an `#anchor` must resolve to a Markdown heading (for `.md`) or a
# YAML key (for everything else).
def validate_manifest_entry!(entry, context, root)
  fail_with("#{context}: source_manifest entry must be a string") unless entry.is_a?(String)
  if entry =~ /:\d/
    fail_with("#{context}: source_manifest entry #{entry.inspect} uses a line-number citation; cite `path` or `path#anchor` instead")
  end

  path, anchor = entry.split("#", 2)
  fail_with("#{context}: source_manifest entry #{entry.inspect} has an empty path") if path.nil? || path.empty?

  abs = File.join(root, path)
  fail_with("#{context}: source_manifest path #{path.inspect} does not exist") unless File.exist?(abs)

  return if anchor.nil? || anchor.empty?

  if path.end_with?(".md")
    unless markdown_heading_slugs(abs).include?(anchor)
      fail_with("#{context}: source_manifest anchor ##{anchor} is not a heading in #{path}")
    end
  elsif !yaml_key?(abs, anchor)
    fail_with("#{context}: source_manifest anchor ##{anchor} is not a key in #{path}")
  end
end

def validate_acceptance!(entry, context)
  kind = entry["kind"]
  fail_with("#{context}: invalid kind #{kind.inspect}") unless %w[ci live].include?(kind)

  has_command = entry.key?("command")
  has_note = entry.key?("note")
  fail_with("#{context}: exactly one of command/note is required") if has_command == has_note

  if has_command
    fail_with("#{context}: command must be non-empty") unless entry["command"].is_a?(String) && !entry["command"].empty?
    success = entry["success"]
    fail_with("#{context}: command entries require success.exit_status") unless success.is_a?(Hash)
    fail_with("#{context}: success only supports exit_status") unless success.keys == ["exit_status"]
    fail_with("#{context}: exit_status must be a non-negative integer") unless success["exit_status"].is_a?(Integer) && success["exit_status"] >= 0
    fail_with("#{context}: command entries cannot be descriptive_only") if entry.key?("descriptive_only")
  else
    fail_with("#{context}: note must be non-empty") unless entry["note"].is_a?(String) && !entry["note"].empty?
    fail_with("#{context}: note entries require descriptive_only: true") unless entry["descriptive_only"] == true
    fail_with("#{context}: note entries cannot define success") if entry.key?("success")
  end
end

def run_acceptance!(entries, root)
  if entries.length < 2
    fail_with("expected at least 2 executable acceptance entries, got #{entries.length}")
  end

  kinds = entries.map { |entry| entry.fetch(:kind) }.uniq
  unless kinds.include?("ci") && kinds.include?("live")
    fail_with("executable acceptance entries must include ci and live kinds")
  end

  entries.each do |entry|
    command = entry.fetch(:command)
    expected = entry.fetch(:exit_status)
    stdout, stderr, status = Open3.capture3(command, chdir: root)
    next if status.exitstatus == expected

    warn stdout unless stdout.empty?
    warn stderr unless stderr.empty?
    fail_with("#{entry.fetch(:context)}: command #{command.inspect} exited #{status.exitstatus}, expected #{expected}")
  end

  puts "validate-surfaces-manifest: executed #{entries.length} acceptance commands"
end

begin
  data = YAML.safe_load(
    File.read(path),
    aliases: false,
    filename: path
  )
  fail_with("top-level document must be a mapping") unless data.is_a?(Hash)
  fail_with("schema_version must be 1") unless data["schema_version"] == 1

  surfaces = data["surfaces"]
  fail_with("surfaces must be an array") unless surfaces.is_a?(Array)

  ids = {}
  ordinals = {}
  executable_entries = []
  surfaces.each do |surface|
    fail_with("surface entries must be mappings") unless surface.is_a?(Hash)
    id = surface["id"]
    ordinal = surface["ordinal"]
    fail_with("surface id must be lowercase hyphenated") unless id.is_a?(String) && id.match?(/\A[a-z0-9][a-z0-9-]*\z/)
    fail_with("duplicate surface id #{id}") if ids[id]
    ids[id] = true
    fail_with("#{id}: ordinal must be an integer") unless ordinal.is_a?(Integer)
    fail_with("duplicate ordinal #{ordinal}") if ordinals[ordinal]
    ordinals[ordinal] = true

    products = surface["products"]
    fail_with("#{id}: products must contain codex, claude, and hermes only") unless products.is_a?(Hash) && products.keys.sort == %w[claude codex hermes]
    products.each do |product, details|
      context = "#{id}.#{product}"
      fail_with("#{context}: details must be a mapping") unless details.is_a?(Hash)
      fail_with("#{context}: invalid state") unless STATE_VALUES.include?(details["state"])
      %w[mechanism min_product min_nils_cli].each do |field|
        fail_with("#{context}: #{field} must be non-empty") unless details[field].is_a?(String) && !details[field].empty?
      end
      fail_with("#{context}: source_artifacts must be an array") unless details["source_artifacts"].is_a?(Array)
      fail_with("#{context}: source_manifest must be a non-empty array") unless details["source_manifest"].is_a?(Array) && !details["source_manifest"].empty?
      details["source_manifest"].each_with_index do |entry, manifest_index|
        validate_manifest_entry!(entry, "#{context}.source_manifest[#{manifest_index}]", root)
      end

      acceptance = details["acceptance"]
      fail_with("#{context}: acceptance must be an array") unless acceptance.is_a?(Array)
      kinds = acceptance.map { |entry| entry["kind"] }
      fail_with("#{context}: acceptance must include ci and live entries") unless kinds.include?("ci") && kinds.include?("live")
      acceptance.each_with_index do |entry, index|
        fail_with("#{context}.acceptance[#{index}]: entry must be a mapping") unless entry.is_a?(Hash)
        validate_acceptance!(entry, "#{context}.acceptance[#{index}]")
        if entry.key?("command")
          executable_entries << {
            context: "#{context}.acceptance[#{index}]",
            kind: entry["kind"],
            command: entry["command"],
            exit_status: entry.fetch("success").fetch("exit_status")
          }
        end
      end
    end
  end
  fail_with("expected 16 surfaces, got #{surfaces.length}") unless surfaces.length == 16
  run_acceptance!(executable_entries, root) if execute_acceptance
rescue Psych::Exception => e
  fail_with("YAML parse failed: #{e.message}")
end

puts "validate-surfaces-manifest: ok #{path}"
RUBY
