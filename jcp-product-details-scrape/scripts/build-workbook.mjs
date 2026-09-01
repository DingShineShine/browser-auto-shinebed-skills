import fs from "node:fs/promises";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";


const cliArgs = process.argv.slice(2);

function argValue(name, fallback) {
  const index = cliArgs.indexOf(name);
  if (index < 0 || index + 1 >= cliArgs.length) return fallback;
  return cliArgs[index + 1];
}

const baseDir = path.resolve(argValue("--base-dir", "."));
const dataPath = path.resolve(argValue("--data-path", path.join(baseDir, "workbook_data.json")));
const outputDir = path.resolve(argValue("--output-dir", path.join(baseDir, "outputs")));
const outputPath = path.resolve(argValue("--output-path", path.join(outputDir, "jcp_alias_first_results.xlsx")));

async function loadArtifactTool() {
  try {
    return await import("@oai/artifact-tool");
  } catch (firstError) {
    const require = createRequire(import.meta.url);
    const candidateRoots = [
      argValue("--module-root", ""),
      process.env.CODEX_ARTIFACT_TOOL_MODULE_ROOT || "",
      path.join(os.homedir(), ".cache", "codex-runtimes", "codex-primary-runtime", "dependencies", "node"),
      baseDir,
      process.cwd(),
    ].filter(Boolean);

    for (const root of candidateRoots) {
      try {
        const resolved = require.resolve("@oai/artifact-tool", { paths: [root] });
        return await import(pathToFileURL(resolved).href);
      } catch {
        // Try the next known runtime/module root.
      }
    }
    throw firstError;
  }
}

const { SpreadsheetFile, Workbook } = await loadArtifactTool();
const workbookData = JSON.parse(await fs.readFile(dataPath, "utf8"));
const workbook = Workbook.create();

const sheetNameMap = new Map([
  ["Group Summary", "分组汇总"],
  ["Alias Map", "Alias Map"],
  ["Source Match", "源表匹配"],
  ["Scraped Variants", "JCP变体"],
  ["Warnings", "Warnings"],
  ["Run Info", "Run Info"],
]);

const columnLabels = {
  source_row: "Source Row",
  source_sku: "SKU",
  seller_sku: "Seller Sku",
  crawl_sku: "JCP SKU",
  sku_name: "SKU Name",
  spu_name: "SPU Name",
  jcp_prefix: "JCP SKU/Web ID Prefix",
  match_status: "Match Status",
  request_sku_original: "Original Request SKU",
  request_sku_used: "Request SKU Used",
  group_source_sku_count: "Group Source SKU Count",
  resolution_status: "Alias/PDP Resolution",
  ppid_count: "Resolved ppId Count",
  source_ppids: "Resolved ppIds",
  pdp_fetch_count: "PDP Fetch Count",
  pdp_fetch_keys: "PDP Fetch Keys",
  alias_ok_count: "Alias OK Count",
  alias_failed_count: "Alias Failed Count",
  alias_status: "Alias Status",
  alias_ppid: "Alias ppId",
  alias_pdp_url: "Alias PDP URL",
  alias_selected_sku_id: "Alias selectedSKUId",
  alias_id: "Alias ID",
  alias_http_status: "Alias HTTP Status",
  alias_message: "Alias Message",
  alias_url: "Alias API URL",
  resolved_at: "Alias Resolved At",
  source_row_count: "Source Row Count",
  source_rows: "Source Rows",
  source_sku_names: "Source SKU Names",
  source_prefixes: "Source Prefixes",
  source_seller_skus: "Source Seller SKUs",
  sku_id: "PDP Variant SKU ID",
  web_id: "PDP Web ID",
  product_id: "Product ID",
  product_name: "Product Name",
  brand: "Brand",
  lot_id: "Lot ID",
  color: "Color",
  color_family: "Color Family",
  color_option_id: "Color Option ID",
  size: "Size",
  primary_barcode: "Primary Barcode",
  secondary_barcode: "Secondary Barcode",
  itsa_status: "ITSA Status",
  source: "JCP Source",
  has_inventory: "Has Inventory",
  atp: "ATP",
  inventory_atp: "Inventory ATP",
  inventory_quality: "Inventory Quality",
  offering_status: "Offering HTTP Status",
  actual_sku_id: "Actual SKU ID",
  marketing_label: "Marketing Label",
  original_price_min: "Original Price Min",
  original_price_max: "Original Price Max",
  sale_price_min: "Sale Price Min",
  sale_price_max: "Sale Price Max",
  sale_percent_off_min: "Sale Percent Off Min",
  sale_percent_off_max: "Sale Percent Off Max",
  coupon_code: "Coupon Code",
  coupon_price_min: "Coupon Price Min",
  coupon_price_max: "Coupon Price Max",
  pricing_inventory: "Pricing Inventory",
  ship_to_home_status: "Ship To Home Status",
  bopus_status: "BOPUS Status",
  my_alert_indicator: "My Alert Indicator",
  image_url: "Image URL",
  swatch_url: "Swatch URL",
  offering_url: "Offering URL",
  scraped_at: "Scraped At",
  current_url: "Current URL",
  raw_file: "Raw JSON",
  group_note: "Group Note",
  group_index: "Group #",
  source_sku_count: "Source SKU Count",
  unique_source_sku_count: "Unique Source SKU Count",
  scrape_ok: "Scrape OK",
  status: "Status",
  fetched_variant_count: "Fetched Variant Count",
  matched_source_row_count: "Matched Source Rows",
  matched_unique_sku_count: "Matched Unique SKUs",
  missing_source_row_count: "Missing Source Rows",
  missing_unique_sku_count: "Missing Unique SKUs",
  extra_variant_count: "Extra Variants",
  coverage_rate: "Coverage Rate",
  warning_count: "Warning Count",
  notes: "Notes",
  source_match_status: "Source Match Status",
  matched_source_rows: "Matched Source Rows",
  matched_source_skus: "Matched Source SKUs",
  matched_seller_skus: "Matched Seller SKUs",
  warning_index: "Warning #",
  warning: "Warning",
  field: "Field",
  value: "Value",
};

const defaultWidths = {
  source_row: 11,
  group_index: 9,
  source_sku_count: 15,
  source_row_count: 15,
  unique_source_sku_count: 18,
  group_source_sku_count: 18,
  ppid_count: 16,
  pdp_fetch_count: 15,
  alias_ok_count: 15,
  alias_failed_count: 17,
  fetched_variant_count: 18,
  matched_source_row_count: 18,
  matched_unique_sku_count: 18,
  missing_source_row_count: 18,
  missing_unique_sku_count: 18,
  extra_variant_count: 14,
  coverage_rate: 13,
  warning_count: 13,
  warning_index: 10,
  scrape_ok: 10,
  status: 17,
  resolution_status: 20,
  alias_status: 18,
  match_status: 26,
  source_match_status: 24,
  source_sku: 16,
  seller_sku: 16,
  crawl_sku: 14,
  sku_id: 16,
  actual_sku_id: 15,
  request_sku_original: 18,
  request_sku_used: 16,
  alias_selected_sku_id: 18,
  alias_id: 18,
  alias_http_status: 16,
  alias_ppid: 18,
  sku_name: 34,
  spu_name: 34,
  jcp_prefix: 18,
  product_name: 48,
  product_id: 18,
  web_id: 12,
  brand: 16,
  lot_id: 12,
  color: 22,
  color_family: 14,
  color_option_id: 15,
  size: 18,
  primary_barcode: 18,
  secondary_barcode: 18,
  itsa_status: 12,
  source: 12,
  has_inventory: 13,
  atp: 10,
  inventory_atp: 13,
  inventory_quality: 16,
  offering_status: 17,
  marketing_label: 20,
  coupon_code: 14,
  pricing_inventory: 17,
  ship_to_home_status: 20,
  bopus_status: 15,
  my_alert_indicator: 17,
  current_url: 58,
  alias_pdp_url: 58,
  alias_url: 64,
  offering_url: 58,
  image_url: 48,
  swatch_url: 48,
  source_rows: 42,
  source_sku_names: 42,
  source_prefixes: 26,
  source_seller_skus: 42,
  source_ppids: 42,
  pdp_fetch_keys: 48,
  raw_file: 56,
  notes: 72,
  group_note: 72,
  alias_message: 72,
  warning: 92,
  field: 26,
  value: 104,
};

const textColumns = new Set([
  "source_sku",
  "seller_sku",
  "crawl_sku",
  "sku_id",
  "web_id",
  "product_id",
  "lot_id",
  "primary_barcode",
  "secondary_barcode",
  "actual_sku_id",
  "request_sku_original",
  "request_sku_used",
  "jcp_prefix",
  "alias_selected_sku_id",
  "alias_id",
  "alias_http_status",
  "alias_ppid",
  "source_ppids",
]);

const currencyColumns = new Set([
  "original_price_min",
  "original_price_max",
  "sale_price_min",
  "sale_price_max",
  "coupon_price_min",
  "coupon_price_max",
]);

const integerColumns = new Set([
  "source_row",
  "group_index",
  "source_sku_count",
  "unique_source_sku_count",
  "source_row_count",
  "group_source_sku_count",
  "ppid_count",
  "pdp_fetch_count",
  "alias_ok_count",
  "alias_failed_count",
  "fetched_variant_count",
  "matched_source_row_count",
  "matched_unique_sku_count",
  "missing_source_row_count",
  "missing_unique_sku_count",
  "extra_variant_count",
  "warning_count",
  "warning_index",
]);

const wrapColumns = new Set([
  "sku_name",
  "spu_name",
  "product_name",
  "marketing_label",
  "current_url",
  "alias_pdp_url",
  "alias_url",
  "offering_url",
  "image_url",
  "swatch_url",
  "source_rows",
  "source_sku_names",
  "source_prefixes",
  "source_seller_skus",
  "source_ppids",
  "pdp_fetch_keys",
  "raw_file",
  "notes",
  "group_note",
  "alias_message",
  "warning",
  "value",
]);

function columnLetter(index) {
  let n = index + 1;
  let letters = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    letters = String.fromCharCode(65 + rem) + letters;
    n = Math.floor((n - 1) / 26);
  }
  return letters;
}

function cleanCell(value) {
  if (value == null) return null;
  if (Array.isArray(value)) return value.join("|");
  if (typeof value === "number" || typeof value === "boolean") return value;
  return String(value);
}

function rangeAddress(rowCount, colCount) {
  return `A1:${columnLetter(colCount - 1)}${Math.max(1, rowCount)}`;
}

function applyColumnFormats(sheet, columns, rowCount) {
  for (const [index, key] of columns.entries()) {
    const col = columnLetter(index);
    sheet.getRange(`${col}:${col}`).format.columnWidth = defaultWidths[key] || 15;
    if (rowCount <= 1) continue;
    const bodyRange = sheet.getRange(`${col}2:${col}${rowCount}`);
    if (textColumns.has(key)) {
      bodyRange.format.numberFormat = "@";
    } else if (currencyColumns.has(key)) {
      bodyRange.format.numberFormat = "$#,##0.00";
    } else if (key === "coverage_rate") {
      bodyRange.format.numberFormat = "0.0%";
    } else if (key.startsWith("sale_percent_off")) {
      bodyRange.format.numberFormat = "0.0";
    } else if (integerColumns.has(key)) {
      bodyRange.format.numberFormat = "#,##0";
    }
    if (wrapColumns.has(key)) {
      bodyRange.format.wrapText = true;
    }
  }
}

function addStatusFormatting(sheet, columns, rowCount) {
  if (rowCount <= 1) return;
  const statusColumns = ["status", "match_status", "source_match_status", "resolution_status", "alias_status"];
  for (const key of statusColumns) {
    const index = columns.indexOf(key);
    if (index < 0) continue;
    const col = columnLetter(index);
    const range = sheet.getRange(`${col}2:${col}${rowCount}`);
    try {
      range.conditionalFormats.add("containsText", {
        text: "failed",
        format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } },
      });
      range.conditionalFormats.add("containsText", {
        text: "missing",
        format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } },
      });
      range.conditionalFormats.add("containsText", {
        text: "partial",
        format: { fill: "#FEF3C7", font: { color: "#92400E", bold: true } },
      });
      range.conditionalFormats.add("containsText", {
        text: "multiple",
        format: { fill: "#FEF3C7", font: { color: "#92400E", bold: true } },
      });
      range.conditionalFormats.add("containsText", {
        text: "unresolved",
        format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } },
      });
      range.conditionalFormats.add("containsText", {
        text: "http_",
        format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } },
      });
      range.conditionalFormats.add("containsText", {
        text: "error",
        format: { fill: "#FEE2E2", font: { color: "#991B1B", bold: true } },
      });
      range.conditionalFormats.add("containsText", {
        text: "warning",
        format: { fill: "#DBEAFE", font: { color: "#1E40AF", bold: true } },
      });
      range.conditionalFormats.add("containsText", {
        text: "matched",
        format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } },
      });
      range.conditionalFormats.add("containsText", {
        text: "ok",
        format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } },
      });
    } catch {
      // Conditional formatting is a scan aid; data remains valid if a renderer skips it.
    }
  }
}

function addSheet(sourceName, tableName) {
  const { columns, rows } = workbookData.sheets[sourceName];
  const sheet = workbook.worksheets.add(sheetNameMap.get(sourceName) || sourceName);
  sheet.showGridLines = false;

  const headers = columns.map((key) => columnLabels[key] || key);
  const matrix = [
    headers,
    ...rows.map((row) => columns.map((key) => cleanCell(row[key]))),
  ];
  const rowCount = matrix.length;
  const colCount = columns.length;
  const used = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  used.values = matrix;
  used.format = {
    font: { size: 10 },
    borders: {
      insideHorizontal: { style: "thin", color: "#E5E7EB" },
    },
  };

  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format = {
    fill: "#1F2937",
    font: { bold: true, color: "#FFFFFF", size: 10 },
    wrapText: true,
  };
  header.format.rowHeight = 32;
  sheet.freezePanes.freezeRows(1);

  if (rowCount > 1) {
    const table = sheet.tables.add(rangeAddress(rowCount, colCount), true, tableName);
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;
  }

  applyColumnFormats(sheet, columns, rowCount);
  addStatusFormatting(sheet, columns, rowCount);

  if (sourceName === "Group Summary" && rowCount > 1) {
    const coverageIndex = columns.indexOf("coverage_rate");
    if (coverageIndex >= 0) {
      const col = columnLetter(coverageIndex);
      try {
        sheet.getRange(`${col}2:${col}${rowCount}`).conditionalFormats.add("colorScale", {
          criteria: [
            { type: "lowestValue", color: "#FCA5A5" },
            { type: "percentile", value: 50, color: "#FDE68A" },
            { type: "highestValue", color: "#86EFAC" },
          ],
        });
      } catch {
        // Nonessential scan aid.
      }
    }
  }

  return { sheet, rowCount, colCount };
}

const created = [
  addSheet("Group Summary", "GroupSummaryTable"),
  addSheet("Alias Map", "AliasMapTable"),
  addSheet("Source Match", "SourceMatchTable"),
  addSheet("Scraped Variants", "ScrapedVariantsTable"),
  addSheet("Warnings", "WarningsTable"),
  addSheet("Run Info", "RunInfoTable"),
];

await fs.mkdir(outputDir, { recursive: true });

const inspection = await workbook.inspect({
  kind: "table",
  sheetId: "分组汇总",
  range: "A1:AD20",
  include: "values",
  tableMaxRows: 20,
  tableMaxCols: 30,
  maxChars: 8000,
});
console.log(inspection.ndjson);

const aliasInspection = await workbook.inspect({
  kind: "table",
  sheetId: "Alias Map",
  range: "A1:O25",
  include: "values",
  tableMaxRows: 25,
  tableMaxCols: 15,
  maxChars: 5000,
});
console.log(aliasInspection.ndjson);

const sourceInspection = await workbook.inspect({
  kind: "table",
  sheetId: "源表匹配",
  range: "A1:R25",
  include: "values",
  tableMaxRows: 25,
  tableMaxCols: 18,
  maxChars: 5000,
});
console.log(sourceInspection.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

for (const { sheet, rowCount, colCount } of created) {
  const previewRows = Math.min(rowCount, 28);
  const previewCols = Math.min(colCount, 16);
  const previewRange = `A1:${columnLetter(previewCols - 1)}${previewRows}`;
  const preview = await workbook.render({
    sheetName: sheet.name,
    range: previewRange,
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(outputDir, `${sheet.name.replace(/[\\/:*?"<>|]/g, "_")}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);

console.log(JSON.stringify({
  outputPath,
  stats: workbookData.stats,
  sheets: Array.from(sheetNameMap.values()),
}, null, 2));
