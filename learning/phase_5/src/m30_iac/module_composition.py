"""
Module Composition — Terraform module system for reusable infrastructure.

WHY THIS MATTERS:
As infrastructure grows, you need reusable building blocks. Terraform
modules let you encapsulate a set of resources (e.g. "VPC + subnets +
route tables") into a reusable unit with a clean interface of input
variables and output values.

Key concepts:
  - Variables: typed inputs to a module. Required variables must be
    provided; optional variables have defaults.
  - Outputs: values exported from a module for use by other modules.
  - Module wiring: connecting the output of one module to the input
    of another (e.g. VPC module's vpc_id output -> EC2 module's
    vpc_id variable).
  - Composition: combining multiple modules into a complete
    infrastructure configuration.
"""

from .resource_graph import Resource, ResourceGraph


class Variable:
    """A typed input variable for a Terraform module.

    Variables define the interface of a module. Each variable has:
    - name: the variable name used in the module configuration.
    - var_type: the expected type (string, number, bool, list, map).
    - default: optional default value. If None, the variable is required.
    - description: documentation for the variable.
    - is_required: True if no default is provided.

    Example in HCL:
        variable "instance_type" {
          type        = string
          default     = "t3.micro"
          description = "EC2 instance type"
        }
    """

    def __init__(
        self,
        name: str,
        var_type: str = "string",
        default=None,
        description: str = "",
        is_required: bool = True,
    ):
        self.name = name
        self.var_type = var_type
        self.default = default
        self.description = description
        self.is_required = is_required


class Output:
    """A value exported from a Terraform module.

    Outputs are how modules communicate: one module's output becomes
    another module's input variable.

    Example in HCL:
        output "vpc_id" {
          value       = aws_vpc.main.id
          description = "The ID of the VPC"
        }
    """

    def __init__(self, name: str, value=None, description: str = ""):
        self.name = name
        self.value = value
        self.description = description


class Module:
    """A Terraform module — a reusable unit of infrastructure.

    A module encapsulates:
    - Variables (inputs): what the caller must/can provide.
    - Resources: the infrastructure the module manages.
    - Outputs: values exported for use by other modules.

    Modules are validated before use: all required variables must be
    provided with the correct types.
    """

    def __init__(self, name: str, variables: list = None, outputs: list = None, resources: list = None):
        self.name = name
        self.variables = variables or []
        self.outputs = outputs or []
        self.resources = resources or []

    def validate_inputs(self, inputs: dict) -> tuple:
        """Validate that the provided inputs satisfy the module's variables.

        Checks:
        1. All required variables are present in inputs.
        2. Provided values match the expected type.

        Args:
            inputs: dict of variable_name -> value.

        Returns:
            A tuple of (is_valid: bool, errors: list[str]).
        """
        errors = []

        for var in self.variables:
            if var.is_required and var.name not in inputs:
                errors.append(f"required variable '{var.name}' is missing")
                continue

            if var.name in inputs:
                value = inputs[var.name]
                if not self._type_matches(value, var.var_type):
                    errors.append(
                        f"variable '{var.name}' expected type '{var.var_type}', "
                        f"got '{type(value).__name__}'"
                    )

        return len(errors) == 0, errors

    def _type_matches(self, value, var_type: str) -> bool:
        """Check if a value matches the expected Terraform type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "bool": bool,
            "list": list,
            "map": dict,
        }
        expected = type_map.get(var_type)
        if expected is None:
            return True  # Unknown type, accept anything
        return isinstance(value, expected)

    def get_output(self, name: str) -> Output:
        """Get a module output by name, or None if not found."""
        for output in self.outputs:
            if output.name == name:
                return output
        return None


class ModuleComposer:
    """Composes multiple modules into a unified resource graph.

    The composer manages:
    - Module registration with their input values.
    - Wiring: connecting outputs of one module to inputs of another.
    - Composition: merging all modules' resources into a single graph.
    - Validation: ensuring all wiring is valid and inputs are satisfied.

    Example:
        composer = ModuleComposer()
        composer.add_module(vpc_module, {"cidr": "10.0.0.0/16"})
        composer.add_module(ec2_module, {})
        composer.wire("vpc", "vpc_id", "ec2", "vpc_id")
        graph = composer.compose()
    """

    def __init__(self):
        self._modules: dict[str, dict] = {}  # name -> {module, inputs}
        self._wiring: list[dict] = []

    def add_module(self, module: Module, inputs: dict = None) -> None:
        """Register a module with its input values."""
        self._modules[module.name] = {
            "module": module,
            "inputs": inputs or {},
        }

    def wire(self, source_module: str, output_name: str, target_module: str, variable_name: str) -> None:
        """Connect an output of one module to an input of another.

        This is how modules communicate: the VPC module's vpc_id output
        feeds into the EC2 module's vpc_id input variable.
        """
        self._wiring.append({
            "source_module": source_module,
            "output_name": output_name,
            "target_module": target_module,
            "variable_name": variable_name,
        })

    def compose(self) -> ResourceGraph:
        """Combine all modules' resources into a single ResourceGraph.

        Resources are namespaced by their module name to avoid ID
        collisions (e.g. "vpc.aws_vpc.main" vs "ec2.aws_vpc.main").

        Returns:
            A ResourceGraph containing all modules' resources.
        """
        graph = ResourceGraph()
        for mod_name, entry in self._modules.items():
            module = entry["module"]
            for resource in module.resources:
                # Namespace the resource by module name
                namespaced = Resource(
                    type=resource.type,
                    name=f"{mod_name}_{resource.name}",
                    properties=resource.properties,
                    depends_on=[
                        f"{resource.type}.{mod_name}_{dep.split('.')[-1]}"
                        if '.' in dep else dep
                        for dep in resource.depends_on
                    ],
                )
                graph.add_resource(namespaced)
        return graph

    def validate(self) -> tuple:
        """Validate the composition.

        Checks:
        1. All modules' required inputs are satisfied (by direct input
           or by wiring from another module's output).
        2. All wiring references valid modules, outputs, and variables.

        Returns:
            A tuple of (is_valid: bool, errors: list[str]).
        """
        errors = []

        # Check wiring references
        for wire in self._wiring:
            src = wire["source_module"]
            tgt = wire["target_module"]
            out_name = wire["output_name"]
            var_name = wire["variable_name"]

            if src not in self._modules:
                errors.append(f"wiring source module '{src}' not found")
                continue
            if tgt not in self._modules:
                errors.append(f"wiring target module '{tgt}' not found")
                continue

            src_module = self._modules[src]["module"]
            if src_module.get_output(out_name) is None:
                errors.append(f"module '{src}' has no output '{out_name}'")

            tgt_module = self._modules[tgt]["module"]
            tgt_var_names = [v.name for v in tgt_module.variables]
            if var_name not in tgt_var_names:
                errors.append(f"module '{tgt}' has no variable '{var_name}'")

        # Check that all required inputs are satisfied
        # Inputs can come from direct inputs or wiring
        wired_inputs: dict[str, set] = {}
        for wire in self._wiring:
            tgt = wire["target_module"]
            var_name = wire["variable_name"]
            if tgt not in wired_inputs:
                wired_inputs[tgt] = set()
            wired_inputs[tgt].add(var_name)

        for mod_name, entry in self._modules.items():
            module = entry["module"]
            direct_inputs = entry["inputs"]
            wired = wired_inputs.get(mod_name, set())

            for var in module.variables:
                if var.is_required and var.name not in direct_inputs and var.name not in wired:
                    errors.append(
                        f"module '{mod_name}': required variable '{var.name}' "
                        f"is not provided and not wired"
                    )

        return len(errors) == 0, errors
