from beet import Context, DataPack, Function, FunctionTag, subproject
import os
import json
import re

load = DataPack("load", path="load")


def scan(ctx: Context):
    modules = [f.path for f in os.scandir("modules") if f.is_dir()]
    ctx.meta["modules"] = dict()
    for m in modules:
        with open(os.path.join(m, "module.json")) as f:
            module = json.load(f)
            ctx.meta["modules"][module["id"]] = module
            ctx.meta["modules"][module["id"]]["path"] = m


def build(ctx: Context):
    for m in ctx.meta["modules"]:
        module = ctx.meta["modules"][m]
        ctx.require(subproject({
            "pipeline": ["plugins.build_module"],
            "data_pack": {
                "load": [module["path"]],
                "name": m,
                "pack_format": ctx.meta["pack_format"]
            },
            "output": "out",
            "meta": {
                "modules": ctx.meta["modules"],
                "module": module
            }
        }))


def build_module(ctx: Context):
    module = ctx.meta["module"]
    id = module["id"]
    short_id = re.sub(r"^gm4_", "", id)
    mainspace = ctx.data[id]
    dependencies = module.get("dependencies", dict())

    ctx.data.description = [
        module["name"] + "\n",
        { "text": "Gamemode 4 for 1.16", "color": "aqua" }
    ]

    if id != "gm4":
        dependencies["gm4"] = ctx.meta["modules"]["gm4"]["version"]

    if dependencies:
        load_function = [f"execute {' '.join([f'if score {d} load matches {dependencies[d]}' for d in dependencies])} run scoreboard players set {id} load {module['version']}"]
    else:
        load_function = [f"scoreboard players set {id} load {module['version']}"]

    for d in dependencies:
        load_function.append(f"execute unless score {d} load matches {dependencies[d]} run data modify storage gm4:load queue append value {{type:\"missing\",module:\"{module['name']}\",require:\"{ctx.meta['modules'][d]['name']}\"}}")
    load_function.append("")
    load_function.append(f"execute if score {id} load matches {module['version']} run function {id}:init")

    init_function = []
    if "init" in mainspace.functions:
        init_function.extend(mainspace.functions["init"].lines)

    init_function.append(f"execute unless score {short_id} gm4_modules matches 1 run data modify storage gm4:log queue append value {{type:\"install\",module:\"{module['name']}\"}}")
    init_function.append(f"scoreboard players set {short_id} gm4_modules 1")
    init_function.append("")

    for e in module.get("entrypoints", []):
        load_function.append(f"execute unless score {id} load matches {module['version']} run schedule clear {id}:{e}")
        init_function.append(f"schedule function {id}:{e} 1t")

    mainspace.functions["load"] = Function(load_function)
    mainspace.functions["init"] = Function(init_function)

    ctx.data.merge(load)

    ctx.data.function_tags["load:load"] = FunctionTag({ "values": [f"#load:{id}"] })
    load_tag = [f"#load:{d}" for d in dependencies]
    load_tag.append(f"{id}:load")
    ctx.data.function_tags[f"load:{id}"] = FunctionTag({ "values": load_tag })

    for d in dependencies:
        ctx.data.function_tags[f"load:{d}"] = FunctionTag({ "values": [] })
