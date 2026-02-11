/**
 * @name Custom sanitizers for log injection
 * @description Defines custom sanitization functions that prevent log injection
 * @kind path-problem
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.ApiGraphs
import semmle.python.security.dataflow.LogInjectionQuery

/**
 * A sanitizer for log injection that recognizes the sanitize_log function.
 */
class SanitizeLogFunction extends LogInjectionQuery::Sanitizer {
  SanitizeLogFunction() {
    // Match any call to sanitize_log function
    exists(DataFlow::CallCfgNode call |
      call.getFunction().(DataFlow::AttrRead).getAttributeName() = "sanitize_log"
      or
      call.getFunction().(DataFlow::ModuleVariableNode).getName() = "sanitize_log"
    |
      this = call
    )
  }
}

/**
 * Additional barrier to prevent taint flow through sanitize_log
 */
class SanitizeLogBarrier extends DataFlow::Node {
  SanitizeLogBarrier() {
    this = API::moduleImport("text_utils")
            .getMember("sanitize_log")
            .getACall()
  }
}
