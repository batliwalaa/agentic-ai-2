import json

class ToolAgent:
    def __init__(self, client, model, tools, available_funcs):
        """
        Initializes the ToolAgent with the given client, model, tools, and available functions.
        Args:
            client: The AISuite client to use for making requests.
            model: The model to use for generating responses.
            tools: A list of tool definitions available to the agent (tool schema OpanAi style).
            available_funcs: A dictionary mapping function names to their implementations.
        """
        self.client = client
        self.tools = tools
        self.model = model
        self.available_funcs = available_funcs
        self.messages = []

        # Diagnostics flags
        self.inspector_mode = False
        self.protocol_dump = False

    # ----------------------------
    # Diagnostics toggles
    # ----------------------------
    def enable_inspector(self, value=True):
        self.inspector_mode = value
        return self

    def enable_protocol_dump(self, value=True):
        self.protocol_dump = value
        return self

    # ----------------------------
    # Pretty-print helpers
    # ----------------------------
    def _print_inspector(self, label, data):
        if not self.inspector_mode:
            return
        print(f"\n=== {label.upper()} ===")
        print(data)

    def _print_protocol(self, label, payload):
        if not self.protocol_dump:
            return
        print(f"\n### PROTOCOL [{label}] ###")
        print(json.dumps(payload, indent=2))

    # ----------------------------
    # Main interaction method
    # ----------------------------
    def ask(self, prompt):
        """
        Runs the ToolAgent with the given prompt.
        Args:
            prompt: The prompt to send to the agent.
        Returns:
            The final response from the agent after executing any tool calls.
        """
        self.messages.append({"role": "user", "content": prompt})

        while True:
            payload = {
                "model": self.model,
                "messages": self.messages,
                "tools": self.tools
            }
            self._print_protocol("REQUEST", payload)
            response = self.client.chat.completions.create(**payload)

            message = response.choices[0].message
            self._print_protocol("RESPONSE", message.model_dump() if hasattr(message, "model_dump") else str(message))            
            self._print_inspector("Assistant Message", message)

            if not message.tool_calls:
                self.messages.append({
                    "role": "assistant",
                    "content": message.content
                })
                return message.content
            
            tool_call = message.tool_calls[0]
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            self._print_inspector("TOOL CALL DETECTED", {
                "name": func_name,
                "args": func_args,
                "id": tool_call.id
            })

            assistant_packet = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": func_name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                ]
            }

            self._print_protocol("ASSISTANT TOOL_CALL PACKET", assistant_packet)
            # Add the assistant's tool call message
            self.messages.append(assistant_packet)

            if func_name not in self.available_funcs:
                tool_response = f"Error: Function '{func_name}' not found."
            else:
                tool_response = self.available_funcs[func_name](**func_args)

            tool_packet = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(tool_response)
            }

            self._print_protocol("TOOL RESPONSE PACKET", tool_packet)
            self.messages.append(tool_packet)