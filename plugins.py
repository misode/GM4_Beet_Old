from beet import Context, DataPack, Function
import os
import json

from beet.library.data_pack import FunctionTag

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
        pack = DataPack(m, path=module["path"])
        pack.description = [
            module["name"] + "\n",
            { "text": "Gamemode 4 for 1.16", "color": "aqua" }
        ]
        pack.pack_format = ctx.meta["pack_format"]

        build_module(ctx, module, pack)
        pack.save("out", overwrite=True)


def build_module(ctx: Context, module, pack: DataPack):
    dependencies = module.get("dependencies", dict())
    if module["id"] != "gm4":
        dependencies["gm4"] = ctx.meta["modules"]["gm4"]["version"]

    if dependencies:
        load_function = [f"execute {' '.join([f'if score {d} load matches {dependencies[d]}' for d in dependencies])} run scoreboard players set {module['id']} load {module['version']}"]
    else:
        load_function = [f"scoreboard players set {module['id']} load {module['version']}"]

    for d in dependencies:
        load_function.append(f"execute unless score {d} load matches {dependencies[d]} run data modify storage gm4:load queue append value {{type:\"missing\",module:\"{module['name']}\",require:\"{ctx.meta['modules'][d]['name']}\"}}")
    load_function.append("")
    load_function.append(f"execute if score {module['id']} load matches {module['version']} run function {module['id']}:init")

    init_function = []
    if f"{module['id']}:init" in pack.functions:
        init_function.extend(pack.functions[f"{module['id']}:init"].lines)

    init_function.append(f"execute unless score {module['id']} gm4_modules matches 1 run data modify storage gm4:log queue append value {{type:\"install\",module:\"{module['name']}\"}}")
    init_function.append(f"scoreboard players set {module['id']} gm4_modules 1")
    init_function.append("")

    for e in module.get("entrypoints", []):
        load_function.append(f"execute unless score {module['id']} load matches {module['version']} run schedule clear {module['id']}:{e}")
        init_function.append(f"schedule function {module['id']}:{e} 1t")

    pack.functions[f"{module['id']}:load"] = Function(load_function)
    pack.functions[f"{module['id']}:init"] = Function(init_function)

    pack.merge(load)

    pack.function_tags["load:load"] = FunctionTag({ "values": [f"#load:{module['id']}"] })
    load_tag = [f"#load:{d}" for d in dependencies]
    load_tag.append(f"{module['id']}:load")
    pack.function_tags[f"load:{module['id']}"] = FunctionTag({ "values": load_tag })

    for d in dependencies:
        pack.function_tags[f"load:{d}"] = FunctionTag({ "values": [] })
