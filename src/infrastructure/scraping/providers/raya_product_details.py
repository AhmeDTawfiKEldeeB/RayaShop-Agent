from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from html import unescape
from queue import Queue
from typing import Any

import httpx


# =============================================================
# PRODUCT DETAILS MODEL
# =============================================================

@dataclass
class RayaProductDetails:
    product_id: int
    url: str

    name: str = ""
    sku: str | None = None

    brand: str | None = None
    category: str | None = None

    short_description: str = ""
    description: str = ""

    specifications: dict[str, str] = field(
        default_factory=dict
    )

    attributes: dict[str, str] = field(
        default_factory=dict
    )

    price: float | None = None
    currency: str = "EGP"

    stock_status: str | None = None

    raw_data: dict[str, Any] = field(
        default_factory=dict
    )


# =============================================================
# PERSISTENT NODE WORKER
# =============================================================

class _NodeWorker:

    JS_CODE = r"""
const readline = require("readline");
const vm = require("vm");

const rl = readline.createInterface({
    input: process.stdin,
    crlfDelay: Infinity
});

function resolveNuxt(expression) {

    const sandbox = {
        window: {}
    };

    vm.runInNewContext(
        "window.__NUXT__ = " +
        expression +
        ";",
        sandbox
    );

    return JSON.stringify(
        sandbox.window.__NUXT__
    );
}

rl.on("line", (line) => {

    try {

        const expression = JSON.parse(line);

        const result = resolveNuxt(
            expression
        );

        process.stdout.write(
            JSON.stringify({
                ok: true,
                data: result
            }) + "\n"
        );

    } catch (error) {

        process.stdout.write(
            JSON.stringify({
                ok: false,
                error: String(error)
            }) + "\n"
        );
    }
});
"""

    def __init__(
        self,
        node_path: str,
    ):
        self.node_path = node_path

        self.process = subprocess.Popen(
            [
                self.node_path,
                "-e",
                self.JS_CODE,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=1,
        )

        self.lock = threading.Lock()

    def resolve(
        self,
        expression: str,
    ) -> dict[str, Any]:

        with self.lock:

            if (
                self.process.stdin is None
                or self.process.stdout is None
            ):
                raise RuntimeError(
                    "Node worker pipes are unavailable."
                )

            # One JSON object = one line.
            payload = (
                json.dumps(
                    expression,
                    ensure_ascii=False,
                )
                + "\n"
            )

            self.process.stdin.write(
                payload.encode("utf-8")
            )

            self.process.stdin.flush()

            response_line = (
                self.process.stdout.readline()
            )

            if not response_line:

                raise RuntimeError(
                    "Node worker terminated "
                    "without returning a response."
                )

            response = json.loads(
                response_line.decode(
                    "utf-8",
                    errors="replace",
                )
            )

            if not response.get("ok"):

                raise RuntimeError(
                    response.get(
                        "error",
                        "Unknown Node error",
                    )
                )

            resolved_json = response[
                "data"
            ]

            parsed = json.loads(
                resolved_json
            )

            if not isinstance(
                parsed,
                dict,
            ):
                raise RuntimeError(
                    "Resolved Nuxt payload "
                    "is not a dictionary."
                )

            return parsed

    def close(self) -> None:

        try:

            if self.process.stdin:
                self.process.stdin.close()

        except Exception:
            pass

        try:

            self.process.terminate()

            self.process.wait(
                timeout=5
            )

        except Exception:

            try:
                self.process.kill()
            except Exception:
                pass


# =============================================================
# NODE WORKER POOL
# =============================================================

class _NodeWorkerPool:

    def __init__(
        self,
        node_path: str,
        size: int,
    ):
        self.workers = [
            _NodeWorker(node_path)
            for _ in range(size)
        ]

        self.queue: Queue[
            _NodeWorker
        ] = Queue()

        for worker in self.workers:
            self.queue.put(worker)

    def resolve(
        self,
        expression: str,
    ) -> dict[str, Any]:

        worker = self.queue.get()

        try:

            return worker.resolve(
                expression
            )

        finally:

            self.queue.put(
                worker
            )

    def close(self) -> None:

        for worker in self.workers:

            worker.close()


# =============================================================
# PRODUCT DETAIL SCRAPER
# =============================================================

class RayaProductDetailsScraper:

    def __init__(
        self,
        timeout: float = 60,
        node_workers: int = 5,
    ):
        self.timeout = timeout

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": (
                "en-US,en;q=0.9"
            ),
        }

        self.node_path = shutil.which(
            "node"
        )

        if not self.node_path:

            raise RuntimeError(
                "Node.js was not found in PATH."
            )

        self.node_workers = _NodeWorkerPool(
            node_path=self.node_path,
            size=node_workers,
        )

    # =========================================================
    # CLOSE
    # =========================================================

    def close(self) -> None:

        self.node_workers.close()

    # =========================================================
    # SCRAPE
    # =========================================================

    async def scrape(
        self,
        product_id: int,
        url: str,
    ) -> RayaProductDetails:

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:

            response = await client.get(
                url
            )

            response.raise_for_status()

            html = response.text

        print(
            f"Fetched product page: "
            f"{product_id}"
        )

        return self._parse(
            product_id=product_id,
            url=url,
            html=html,
        )

    # =========================================================
    # PARSER
    # =========================================================

    def _parse(
        self,
        *,
        product_id: int,
        url: str,
        html: str,
    ) -> RayaProductDetails:

        details = RayaProductDetails(
            product_id=product_id,
            url=url,
        )

        # -----------------------------------------------------
        # JSON-LD
        # -----------------------------------------------------

        jsonld_objects = (
            self._extract_jsonld(
                html
            )
        )

        product_jsonld = (
            self._find_product_jsonld(
                jsonld_objects
            )
        )

        if product_jsonld:

            self._apply_jsonld(
                details,
                product_jsonld,
            )

        # -----------------------------------------------------
        # NUXT
        # -----------------------------------------------------

        if "window.__NUXT__" in html:

            print(
                "✓ window.__NUXT__ found"
            )

            nuxt = self._execute_nuxt(
                html
            )

            if nuxt is not None:

                print(
                    "✓ Nuxt payload resolved"
                )

                product = (
                    self._find_product_object(
                        nuxt
                    )
                )

                if product:

                    print(
                        "✓ Nuxt product object found"
                    )

                    self._apply_nuxt_product(
                        details,
                        product,
                    )

                else:

                    print(
                        "⚠ Nuxt product object "
                        "was not found"
                    )

            else:

                print(
                    "⚠ Failed to resolve "
                    "Nuxt payload"
                )

        else:

            print(
                "⚠ window.__NUXT__ not found"
            )

        self._normalize_details(
            details
        )

        return details

    # =========================================================
    # JSON-LD
    # =========================================================

    def _extract_jsonld(
        self,
        html: str,
    ) -> list[Any]:

        scripts = re.findall(
            r'<script[^>]+'
            r'type=["\']application/ld\+json["\']'
            r'[^>]*>'
            r'(.*?)'
            r'</script>',
            html,
            flags=(
                re.IGNORECASE
                | re.DOTALL
            ),
        )

        objects = []

        for script in scripts:

            script = script.strip()

            if not script:
                continue

            try:

                objects.append(
                    json.loads(
                        script
                    )
                )

            except json.JSONDecodeError:

                continue

        return objects

    def _find_product_jsonld(
        self,
        objects: list[Any],
    ) -> dict[str, Any] | None:

        for obj in objects:

            if not isinstance(
                obj,
                dict,
            ):
                continue

            if (
                obj.get("@type")
                == "Product"
            ):
                return obj

            graph = obj.get(
                "@graph"
            )

            if not isinstance(
                graph,
                list,
            ):
                continue

            for item in graph:

                if (
                    isinstance(
                        item,
                        dict,
                    )
                    and item.get(
                        "@type"
                    )
                    == "Product"
                ):

                    return item

        return None

    # =========================================================
    # APPLY JSON-LD
    # =========================================================

    def _apply_jsonld(
        self,
        details: RayaProductDetails,
        product: dict[str, Any],
    ) -> None:

        name = product.get(
            "name"
        )

        if name:
            details.name = (
                self._clean_text(name)
            )

        sku = product.get(
            "sku"
        )

        if sku:
            details.sku = (
                self._clean_text(sku)
            )

        brand = product.get(
            "brand"
        )

        if isinstance(
            brand,
            dict,
        ):

            brand_name = brand.get(
                "name"
            )

            if brand_name:

                details.brand = (
                    self._clean_text(
                        brand_name
                    )
                )

        elif isinstance(
            brand,
            str,
        ):

            details.brand = (
                self._clean_text(
                    brand
                )
            )

        description = product.get(
            "description"
        )

        if description:

            details.description = (
                self._clean_html(
                    str(description)
                )
            )

        offers = product.get(
            "offers"
        )

        if isinstance(
            offers,
            dict,
        ):

            price = offers.get(
                "price"
            )

            if price is not None:

                try:

                    details.price = float(
                        price
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    pass

            currency = offers.get(
                "priceCurrency"
            )

            if currency:

                details.currency = str(
                    currency
                )

            availability = (
                offers.get(
                    "availability"
                )
            )

            if availability:

                details.stock_status = (
                    str(
                        availability
                    )
                    .split("/")
                    [-1]
                )

    # =========================================================
    # NUXT
    # =========================================================

    def _execute_nuxt(
        self,
        html: str,
    ) -> dict[str, Any] | None:

        expression = (
            self._extract_nuxt_expression(
                html
            )
        )

        if not expression:

            print(
                "⚠ Could not extract "
                "Nuxt expression"
            )

            return None

        try:

            return (
                self.node_workers.resolve(
                    expression
                )
            )

        except Exception as exc:

            print(
                "⚠ Nuxt resolver error: "
                f"{exc}"
            )

            return None

    def _extract_nuxt_expression(
        self,
        html: str,
    ) -> str | None:

        marker = (
            "window.__NUXT__"
        )

        start = html.find(
            marker
        )

        if start == -1:
            return None

        equals = html.find(
            "=",
            start,
        )

        if equals == -1:
            return None

        script_end = html.find(
            "</script>",
            equals,
        )

        if script_end == -1:

            script_end = html.find(
                "</head>",
                equals,
            )

        if script_end == -1:
            return None

        expression = html[
            equals + 1:script_end
        ].strip()

        if expression.endswith(
            ";"
        ):

            expression = (
                expression[:-1]
                .rstrip()
            )

        return expression

    # =========================================================
    # FIND PRODUCT OBJECT
    # =========================================================

    def _find_product_object(
        self,
        value: Any,
    ) -> dict[str, Any] | None:

        if isinstance(
            value,
            dict,
        ):

            if (
                "name" in value
                and (
                    "short_description"
                    in value
                    or "description"
                    in value
                    or "specification_attributes"
                    in value
                    or "mainCategory"
                    in value
                )
            ):

                return value

            for child in value.values():

                found = (
                    self._find_product_object(
                        child
                    )
                )

                if found:
                    return found

        elif isinstance(
            value,
            list,
        ):

            for item in value:

                found = (
                    self._find_product_object(
                        item
                    )
                )

                if found:
                    return found

        return None

    # =========================================================
    # APPLY NUXT PRODUCT
    # =========================================================

    def _apply_nuxt_product(
        self,
        details: RayaProductDetails,
        product: dict[str, Any],
    ) -> None:

        name = product.get(
            "name"
        )

        if name:

            details.name = (
                self._clean_text(
                    name
                )
            )

        sku = product.get(
            "sku"
        )

        if sku:

            details.sku = (
                self._clean_text(
                    sku
                )
            )

        brand = product.get(
            "brand"
        )

        if isinstance(
            brand,
            dict,
        ):

            brand_name = brand.get(
                "name"
            )

            if brand_name:

                details.brand = (
                    self._clean_text(
                        brand_name
                    )
                )

        main_category = product.get(
            "mainCategory"
        )

        if main_category:

            details.category = (
                self._clean_text(
                    main_category
                )
            )

        if not details.category:

            categories = product.get(
                "categories"
            )

            if isinstance(
                categories,
                list,
            ):

                category_names = []

                for category in categories:

                    if not isinstance(
                        category,
                        dict,
                    ):
                        continue

                    category_name = (
                        category.get(
                            "name"
                        )
                    )

                    if category_name:

                        category_names.append(
                            self._clean_text(
                                category_name
                            )
                        )

                if category_names:

                    details.category = (
                        category_names[0]
                    )

        short_description = (
            product.get(
                "short_description"
            )
        )

        short_text = (
            self._extract_html_field(
                short_description
            )
        )

        if short_text:

            details.short_description = (
                short_text
            )

        description = product.get(
            "description"
        )

        description_text = (
            self._extract_html_field(
                description
            )
        )

        if description_text:

            details.description = (
                description_text
            )

        specification_attributes = (
            product.get(
                "specification_attributes"
            )
        )

        details.specifications = (
            self._parse_specifications(
                specification_attributes
            )
        )

        attributes = product.get(
            "attributes"
        )

        details.attributes = (
            self._parse_attributes(
                attributes
            )
        )

        price = product.get(
            "price"
        )

        if price is not None:

            try:

                details.price = float(
                    price
                )

            except (
                TypeError,
                ValueError,
            ):

                pass

        stock_status = product.get(
            "stock_status"
        )

        if stock_status:

            details.stock_status = (
                self._clean_text(
                    stock_status
                )
            )

        elif "stock" in product:

            stock = product.get(
                "stock"
            )

            if stock is not None:

                details.stock_status = (
                    self._clean_text(
                        stock
                    )
                )

        details.raw_data[
            "product"
        ] = product

    # =========================================================
    # HTML FIELD
    # =========================================================

    def _extract_html_field(
        self,
        value: Any,
    ) -> str:

        if value is None:
            return ""

        if isinstance(
            value,
            dict,
        ):

            html = value.get(
                "html"
            )

            if html is not None:

                return self._clean_html(
                    str(html)
                )

            text = value.get(
                "text"
            )

            if text is not None:

                return self._clean_text(
                    text
                )

        if isinstance(
            value,
            str,
        ):

            return self._clean_html(
                value
            )

        return ""

    # =========================================================
    # SPECIFICATIONS
    # =========================================================

    def _parse_specifications(
        self,
        values: Any,
    ) -> dict[str, str]:

        result: dict[str, str] = {}

        if not isinstance(
            values,
            list,
        ):
            return result

        for item in values:

            if not isinstance(
                item,
                dict,
            ):
                continue

            label = (
                item.get(
                    "label"
                )
                or item.get(
                    "name"
                )
                or item.get(
                    "attribute_label"
                )
                or item.get(
                    "key"
                )
            )

            value = (
                item.get(
                    "value"
                )
                or item.get(
                    "text"
                )
                or item.get(
                    "attribute_value"
                )
            )

            if (
                label is None
                or value is None
            ):
                continue

            label_text = (
                self._clean_text(
                    label
                )
            )

            value_text = (
                self._clean_text(
                    value
                )
            )

            if (
                label_text
                and value_text
            ):

                result[
                    label_text
                ] = value_text

        return result

    # =========================================================
    # ATTRIBUTES
    # =========================================================

    def _parse_attributes(
        self,
        values: Any,
    ) -> dict[str, str]:

        result: dict[str, str] = {}

        if not isinstance(
            values,
            list,
        ):
            return result

        for item in values:

            if not isinstance(
                item,
                dict,
            ):
                continue

            label = (
                item.get(
                    "label"
                )
                or item.get(
                    "name"
                )
                or item.get(
                    "key"
                )
            )

            value = (
                item.get(
                    "value"
                )
                or item.get(
                    "text"
                )
            )

            if (
                label is None
                or value is None
            ):
                continue

            label_text = (
                self._clean_text(
                    label
                )
            )

            value_text = (
                self._clean_text(
                    value
                )
            )

            if (
                label_text
                and value_text
            ):

                result[
                    label_text
                ] = value_text

        return result

    # =========================================================
    # NORMALIZATION
    # =========================================================

    def _normalize_details(
        self,
        details: RayaProductDetails,
    ) -> None:

        details.name = (
            self._clean_text(
                details.name
            )
        )

        if details.sku:

            details.sku = (
                self._clean_text(
                    details.sku
                )
            )

        if details.brand:

            details.brand = (
                self._clean_text(
                    details.brand
                )
            )

        if details.category:

            details.category = (
                self._clean_text(
                    details.category
                )
            )

        details.short_description = (
            self._clean_text(
                details.short_description
            )
        )

        details.description = (
            self._clean_text(
                details.description
            )
        )

        if details.stock_status:

            details.stock_status = (
                self._clean_text(
                    details.stock_status
                )
            )

    # =========================================================
    # TEXT HELPERS
    # =========================================================

    @staticmethod
    def _clean_text(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = unescape(
            str(value)
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    @classmethod
    def _clean_html(
        cls,
        value: str,
    ) -> str:

        value = re.sub(
            r"<br\s*/?>",
            "\n",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"</p\s*>",
            "\n",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"</li\s*>",
            "\n",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"<[^>]+>",
            " ",
            value,
        )

        value = unescape(
            value
        )

        lines = []

        for line in value.splitlines():

            cleaned = cls._clean_text(
                line
            )

            if cleaned:

                lines.append(
                    cleaned
                )

        return "\n".join(
            lines
        )