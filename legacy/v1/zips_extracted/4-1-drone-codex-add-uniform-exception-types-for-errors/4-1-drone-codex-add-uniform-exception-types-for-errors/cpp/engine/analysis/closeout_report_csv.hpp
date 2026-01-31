#pragma once
// ============================================================================
// Closeout Report CSV Writers
// File: cpp/engine/analysis/closeout_report_csv.hpp
// ============================================================================
//
// Purpose:
// - Serialize closeout evidence and gate results to CSV format.
// - Used by closeout_cli tool to write output files.
//
// ============================================================================

#include "engine/closeout/closeout_pipeline.hpp"

#include <iosfwd>

namespace lift::analysis {

// Write evidence items to CSV format
// CSV format: key,value,units,source,notes
void write_closeout_evidence_csv(std::ostream& os, const lift::closeout::CloseoutOutput& out);

// Write gate check results to CSV format  
// CSV format: id,pass,value,threshold,note
void write_closeout_gates_csv(std::ostream& os, const lift::closeout::CloseoutOutput& out);

} // namespace lift::analysis
